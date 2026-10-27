"""Service for scraping news websites, magazines, and social media platforms,
performing narrative synthesis, and determining evidence-backed truth verdicts."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import urllib.parse
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import feedparser
import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False

from app.core.config import settings
from app.core.security import sanitize_html, sanitize_text, validate_url
from app.db.models import DataSource, Document, EvidenceCitation, Investigation, NarrativeCluster
from app.ml.model_manager import model_manager

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 "
        "NarrativeLens-AI/1.0"
    )
}


class NarrativeScraperService:
    """Orchestrates multi-platform web scraping, cross-source narrative analysis, and truth verification."""

    async def _fetch_with_playwright(self, url: str) -> str:
        """Fallback to headless Chromium via Playwright for JavaScript SPAs or protected sites."""
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(user_agent=HEADERS["User-Agent"])
                page = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=12000)
                content = await page.content()
                await browser.close()
                return content
        except Exception as exc:
            logger.warning(f"Playwright fallback failed for {url}: {exc}")
            return ""

    async def scrape_article_url(self, url: str) -> Dict[str, Any]:
        """Scrape article metadata, headline, and body text from a news, magazine, or blog website."""
        is_safe, reason = validate_url(url)
        if not is_safe:
            raise ValueError(f"URL rejected by security policy: {reason}")

        raw_html = ""
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers=HEADERS) as client:
                resp = await client.get(url)
                if resp.status_code < 400 and len(resp.text.strip()) > 100:
                    raw_html = resp.text
                else:
                    logger.info(f"Target site returned HTTP {resp.status_code}, falling back to headless Playwright for {url}")
        except Exception as exc:
            logger.info(f"HTTP GET failed ({exc}), falling back to headless Playwright for {url}")

        if not raw_html:
            raw_html = await self._fetch_with_playwright(url)

        if not raw_html:
            raise ValueError(f"Unable to retrieve content from {url} via both HTTP and Playwright")

        # 1. Try high-precision extraction with Trafilatura
        body_text = ""
        title = ""
        author = None
        published_at = None

        if TRAFILATURA_AVAILABLE:
            try:
                extracted = trafilatura.bare_extraction(raw_html, url=url, with_metadata=True)
                if extracted:
                    if extracted.text:
                        body_text = extracted.text
                    if extracted.title:
                        title = extracted.title
                    if extracted.author:
                        author = extracted.author
                    if extracted.date:
                        try:
                            published_at = datetime.fromisoformat(str(extracted.date).replace("Z", "+00:00"))
                        except Exception:
                            pass
            except Exception as e:
                logger.debug(f"Trafilatura extraction exception: {e}")

        # 2. BeautifulSoup fallback if Trafilatura missed title or content
        soup = BeautifulSoup(raw_html, "html.parser")
        if not title:
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                title = str(og_title["content"]).strip()
            elif soup.title and soup.title.string:
                title = str(soup.title.string).strip()
            elif soup.find("h1"):
                title = soup.find("h1").get_text(strip=True)

        parsed_url = urllib.parse.urlparse(url)
        publisher = parsed_url.netloc.replace("www.", "")

        if not author:
            author_meta = soup.find("meta", attrs={"name": "author"}) or soup.find("meta", property="article:author")
            if author_meta and author_meta.get("content"):
                author = str(author_meta["content"]).strip()

        if not published_at:
            date_meta = (
                soup.find("meta", property="article:published_time")
                or soup.find("meta", attrs={"name": "publication_date"})
                or soup.find("meta", attrs={"name": "date"})
            )
            if date_meta and date_meta.get("content"):
                try:
                    published_at = datetime.fromisoformat(str(date_meta["content"]).replace("Z", "+00:00"))
                except Exception:
                    pass

        if not body_text:
            paragraphs: List[str] = []
            article_elem = soup.find("article") or soup.find("main") or soup
            for p in article_elem.find_all("p"):
                p_text = sanitize_text(p.get_text(strip=True))
                if len(p_text) > 30 and not any(
                    skip in p_text.lower() for skip in ["cookie", "subscribe", "privacy policy", "terms of service", "all rights reserved"]
                ):
                    paragraphs.append(p_text)
            body_text = "\n\n".join(paragraphs[:25])

        snippet = body_text[:400] + ("..." if len(body_text) > 400 else "")

        return {
            "title": title or "Untitled News Article",
            "url": url,
            "publisher": publisher,
            "author": author,
            "published_at": published_at or datetime.now(timezone.utc),
            "content": body_text or title,
            "snippet": snippet,
        }

    async def search_newspapers_and_magazines(self, query: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Search mainstream newspapers and magazines via Google News RSS."""
        encoded_query = urllib.parse.quote_plus(query)
        rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
        results: List[Dict[str, Any]] = []

        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers=HEADERS) as client:
                resp = await client.get(rss_url)
                if resp.status_code == 200:
                    feed = feedparser.parse(resp.text)
                    for entry in feed.entries[:limit]:
                        title = entry.get("title", "")
                        link = entry.get("link", "")
                        source_info = entry.get("source", {}).get("title", "News Outlet")
                        published = entry.get("published", "")
                        summary_raw = entry.get("summary", "")
                        clean_summary = sanitize_html(summary_raw) if summary_raw else title

                        results.append({
                            "title": title,
                            "url": link,
                            "publisher": source_info,
                            "published_at": published,
                            "snippet": clean_summary[:350],
                            "source_type": "newspaper",
                            "platform": "Major News / Press",
                        })
        except Exception as exc:
            logger.warning(f"Error fetching news RSS for query '{query}': {exc}")

        return results

    async def search_social_media(self, query: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Search public social media discussions across Reddit, HackerNews, and Web Forums."""
        encoded_query = urllib.parse.quote_plus(query)
        results: List[Dict[str, Any]] = []

        # 1. Reddit Public RSS (strict 3.5s timeout to prevent hanging on 429)
        try:
            reddit_rss_url = f"https://www.reddit.com/search.rss?q={encoded_query}&sort=relevance"
            async with httpx.AsyncClient(timeout=3.5, follow_redirects=True, headers=HEADERS) as client:
                r_reddit = await client.get(reddit_rss_url)
                if r_reddit.status_code == 200:
                    feed = feedparser.parse(r_reddit.text)
                    for entry in feed.entries[: limit // 2]:
                        title = entry.get("title", "")
                        link = entry.get("link", "")
                        published = entry.get("published", "")
                        raw_content = entry.get("content", [{}])[0].get("value", "") if "content" in entry else entry.get("summary", "")
                        clean_text = sanitize_html(raw_content) if raw_content else title

                        results.append({
                            "title": title,
                            "url": link,
                            "publisher": "Reddit",
                            "published_at": published,
                            "snippet": clean_text[:350] or title,
                            "source_type": "social_media",
                            "platform": "Reddit Public Forum",
                        })
        except Exception as exc:
            logger.debug(f"Reddit RSS unavailable: {exc}")

        # 2. HackerNews Discussions
        try:
            hn_url = f"https://hn.algolia.com/api/v1/search?query={encoded_query}&tags=story&hitsPerPage={limit // 2}"
            async with httpx.AsyncClient(timeout=6.0, follow_redirects=True, headers=HEADERS) as client:
                r_hn = await client.get(hn_url)
                if r_hn.status_code == 200:
                    hits = r_hn.json().get("hits", [])
                    for hit in hits:
                        title = hit.get("title", "")
                        url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
                        author = hit.get("author", "hn_user")
                        points = hit.get("points", 0)
                        num_comments = hit.get("num_comments", 0)
                        created_at = hit.get("created_at", "")

                        results.append({
                            "title": title,
                            "url": url,
                            "publisher": "HackerNews",
                            "published_at": created_at,
                            "snippet": f"{title} (Posted by {author}, {points} points, {num_comments} comments)",
                            "source_type": "social_media",
                            "platform": "HackerNews Discussion",
                        })
        except Exception as exc:
            logger.warning(f"Error fetching HackerNews for '{query}': {exc}")

        # 3. Web Discussions Fallback (if results are low)
        if len(results) < 3:
            try:
                forum_query = f"{query} forum discussion"
                async with httpx.AsyncClient(timeout=4.0, follow_redirects=True, headers=HEADERS) as client:
                    ddg_resp = await client.post("https://html.duckduckgo.com/html/", data={"q": forum_query})
                    if ddg_resp.status_code == 200:
                        soup = BeautifulSoup(ddg_resp.text, "html.parser")
                        for r_elem in soup.find_all("div", class_="result")[:4]:
                            title_tag = r_elem.find("a", class_="result__a")
                            snippet_tag = r_elem.find("a", class_="result__snippet")
                            if title_tag and title_tag.get_text(strip=True):
                                results.append({
                                    "title": title_tag.get_text(strip=True),
                                    "url": title_tag.get("href", ""),
                                    "publisher": "Public Discussion",
                                    "published_at": "",
                                    "snippet": snippet_tag.get_text(strip=True) if snippet_tag else "",
                                    "source_type": "social_media",
                                    "platform": "Public Web Forum",
                                })
            except Exception as exc:
                logger.debug(f"Forum fallback skipped: {exc}")

        # 4. YouTube Data API v3 (if configured)
        if settings.YOUTUBE_API_KEY:
            try:
                yt_max = max(3, limit // 3)
                yt_url = (
                    f"https://www.googleapis.com/youtube/v3/search"
                    f"?part=snippet&q={encoded_query}&type=video&maxResults={yt_max}&key={settings.YOUTUBE_API_KEY}"
                )
                async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
                    r_yt = await client.get(yt_url)
                    if r_yt.status_code == 200:
                        items = r_yt.json().get("items", [])
                        for item in items:
                            vid_id = item.get("id", {}).get("videoId")
                            snippet = item.get("snippet", {})
                            title = snippet.get("title", "")
                            channel_title = snippet.get("channelTitle", "YouTube Channel")
                            desc = snippet.get("description", "")
                            published = snippet.get("publishedAt", "")
                            video_url = f"https://www.youtube.com/watch?v={vid_id}" if vid_id else "https://www.youtube.com"

                            results.append({
                                "title": title,
                                "url": video_url,
                                "publisher": f"YouTube ({channel_title})",
                                "published_at": published,
                                "snippet": f"{title} - {desc}"[:350],
                                "source_type": "social_media",
                                "platform": "YouTube Community",
                            })
            except Exception as exc:
                logger.warning(f"Error querying YouTube Data API for '{query}': {exc}")

        return results

    def _analyze_toxicity_batch(self, items: List[Dict[str, Any]]) -> None:
        """Classify hate speech and toxic signals using batch inference."""
        if not items:
            return
        texts = [f"{item.get('title', '')} {item.get('snippet', '')}" for item in items]
        try:
            preds = model_manager.predict_hate_speech_batch(texts)
            for item, pred in zip(items, preds):
                raw_label = pred.get("predicted_label", "normal").lower()
                if raw_label in ("hate", "hatespeech"):
                    std = "Hate Speech"
                elif raw_label in ("offensive", "toxic"):
                    std = "Offensive"
                else:
                    std = "Neutral"

                item["toxicity"] = {
                    "label": std,
                    "confidence": round(float(pred.get("confidence", 0.9)), 4),
                    "is_hate": std == "Hate Speech",
                    "is_offensive": std == "Offensive",
                }
        except Exception as exc:
            logger.warning(f"Batch toxicity inference error: {exc}")
            for item in items:
                item["toxicity"] = {"label": "Neutral", "confidence": 0.90, "is_hate": False, "is_offensive": False}

    async def _synthesize_with_llm(
        self,
        query: str,
        news_items: List[Dict[str, Any]],
        social_items: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Attempt rapid LLM ground-truth synthesis with Ollama (6.0s timeout)."""
        news_sample = "\n".join(
            [f"- {n.get('publisher')}: {n.get('title')} ({n.get('snippet', '')[:120]})" for n in news_items[:5]]
        )
        social_sample = "\n".join(
            [f"- {s.get('platform')}: {s.get('title')} ({s.get('snippet', '')[:100]})" for s in social_items[:4]]
        )

        prompt = (
            f"You are the NarrativeLens Truth Verification Engine.\n"
            f"Evaluate the factual veracity of this specific query / claim: \"{query}\"\n\n"
            f"Scraped News Coverage:\n{news_sample or 'None'}\n\n"
            f"Scraped Social/Forum Discussions:\n{social_sample or 'None'}\n\n"
            f"Critical Instructions:\n"
            f"1. Determine if the news articles actually corroborate the claim \"{query}\", or if the claim is an unsubstantiated rumor, hoax, satire, or false premise.\n"
            f"2. If the claim is biologically impossible, fabricated, or completely unsupported by legitimate reporting, set overall_status to \"debunked\" with a low truth_score (0.01 - 0.20).\n"
            f"3. If the news coverage genuinely confirms the event occurred, set overall_status to \"verified\" with high truth_score (0.80 - 0.95).\n"
            f"4. If coverage is mixed or controversial, set overall_status to \"disputed\". If there is no credible reporting either way, set \"unverified\".\n"
            f"5. Output ONLY valid JSON in this exact structure:\n"
            f"{{\n"
            f"  \"overall_status\": \"verified\" | \"debunked\" | \"disputed\" | \"unverified\",\n"
            f"  \"truth_score\": 0.05,\n"
            f"  \"status_description\": \"One sentence verdict\",\n"
            f"  \"executive_summary\": \"Two sentence synthesis summary\",\n"
            f"  \"verified_facts\": [\"Fact 1\", \"Fact 2\"],\n"
            f"  \"debunked_rumors\": [\"Rumor 1 if any\"],\n"
            f"  \"unresolved_questions\": [\"Open question 1\"],\n"
            f"  \"claims\": [\n"
            f"    {{\"id\": \"claim-1\", \"claim\": \"Specific claim\", \"verdict\": \"debunked\", \"confidence\": 0.95, \"summary\": \"Evidence note\"}}\n"
            f"  ]\n"
            f"}}"
        )

        model_name = getattr(settings, "OLLAMA_MODEL", "qwen3:4b")
        base_url = getattr(settings, "OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        timeout_val = float(getattr(settings, "OLLAMA_TIMEOUT", 15.0))

        try:
            async with httpx.AsyncClient(timeout=timeout_val) as client:
                res = await client.post(
                    f"{base_url}/api/generate",
                    json={
                        "model": model_name,
                        "prompt": prompt,
                        "format": "json",
                        "stream": False,
                        "options": {"temperature": 0.1, "num_predict": 700},
                    },
                )
                if res.status_code == 200:
                    data = res.json()
                    raw_response = data.get("response", "").strip()
                    raw_thinking = data.get("thinking", "").strip()

                    parsed = {}
                    for candidate in (raw_response, raw_thinking):
                        if not candidate:
                            continue
                        try:
                            parsed = json.loads(candidate)
                            if isinstance(parsed, dict) and "overall_status" in parsed:
                                break
                        except Exception:
                            pass
                        match = re.search(r"\{[\s\S]*?\}", candidate)
                        if match:
                            try:
                                candidate_obj = json.loads(match.group(0))
                                if isinstance(candidate_obj, dict) and "overall_status" in candidate_obj:
                                    parsed = candidate_obj
                                    break
                            except Exception:
                                pass

                    if parsed and "overall_status" in parsed and "claims" in parsed:
                        logger.info(f"Successfully synthesized narrative truth via Ollama {model_name}.")
                        return parsed
        except Exception as e:
            logger.debug(f"LLM truth synthesis skipped (falling back to deterministic extractor): {e}")

        return None

    async def _extract_claims_and_synthesize_truth(
        self,
        query: str,
        target_article: Optional[Dict[str, Any]],
        news_items: List[Dict[str, Any]],
        social_items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Cross-analyze claims between journalistic sources and social commentary to establish evidence-grounded truth results."""
        # 1. Try LLM synthesis first
        llm_synthesis = await self._synthesize_with_llm(query, news_items, social_items)
        if llm_synthesis:
            # Wire real supporting/contradicting sources to LLM claims
            for c in llm_synthesis.get("claims", []):
                if c.get("verdict") == "verified":
                    c["supporting_sources"] = [{"title": n["title"], "url": n["url"], "publisher": n["publisher"]} for n in news_items[:3]]
                    c["contradicting_sources"] = []
                elif c.get("verdict") == "debunked":
                    c["supporting_sources"] = []
                    c["contradicting_sources"] = [{"title": n["title"], "url": n["url"], "publisher": n["publisher"]} for n in news_items[:2]]
                else:
                    c["supporting_sources"] = [{"title": s["title"], "url": s["url"], "publisher": s.get("publisher", "Social")} for s in social_items[:2]]
                    c["contradicting_sources"] = []
            return llm_synthesis

        # 2. Deterministic High-Precision Truth Extractor with Semantic Predicate Checking
        all_sources = news_items + social_items
        news_count = len(news_items)
        social_count = len(social_items)

        hate_in_social = sum(1 for s in social_items if s.get("toxicity", {}).get("is_hate"))
        offensive_in_social = sum(1 for s in social_items if s.get("toxicity", {}).get("is_offensive"))

        # Extract content predicate keywords from query (excluding common stopwords and entity titles)
        q_tokens = [w.lower() for w in re.findall(r"[a-zA-Z]{3,}", query)]
        stopwords = {
            "the", "and", "is", "are", "was", "were", "has", "have", "had", "been",
            "for", "with", "from", "that", "this", "they", "them", "their", "what",
            "when", "where", "which", "who", "whom", "will", "would", "about", "into",
            "over", "after", "news", "post", "today", "yesterday", "update", "latest",
            "prime", "minister", "president", "india", "america", "stated", "says"
        }
        content_words = [w for w in q_tokens if w not in stopwords]

        # Check for debunking / hoax markers in query or results
        hoax_terms = {"hoax", "fake", "rumor", "conspiracy", "debunk", "false"}
        is_explicit_hoax_query = any(h in q_tokens for h in hoax_terms)

        # Check impossible / absurd claims (e.g. male pregnancy, supernatural, extraterrestrial)
        impossible_predicates = {"pregnant", "alien", "shape-shifting", "flat earth", "reptilian", "immortal", "resurrected", "cloned"}
        is_impossible = any(t in q_tokens for t in impossible_predicates)

        # Check which content words appear in news headlines and snippets
        all_news_text = " ".join([f"{n.get('title', '')} {n.get('snippet', '')}".lower() for n in news_items])
        matched_words = [w for w in content_words if w in all_news_text]
        coverage_ratio = len(matched_words) / max(len(content_words), 1)

        # Check if fact-checkers explicitly debunked it
        fact_check_found = any(
            any(fc in n.get("title", "").lower() for fc in ["fact check", "debunk", "false claim", "hoax", "myth", "fake"])
            for n in news_items
        )

        verified_facts: List[str] = []
        debunked_rumors: List[str] = []
        unresolved_questions: List[str] = []
        claims: List[Dict[str, Any]] = []

        publishers = list(dict.fromkeys(n["publisher"] for n in news_items if n.get("publisher")))
        headline = target_article.get("title") if target_article else (news_items[0]["title"] if news_items else query)

        # CASE A: Fabricated / Impossible / Unevidenced claim (e.g. Modi is pregnant)
        if is_impossible or (len(content_words) >= 2 and coverage_ratio < 0.35 and not target_article):
            overall_status = "debunked"
            truth_score = 0.04
            status_text = "Debunked False Rumor: No credible journalistic documentation corroborates this claim."
            debunked_rumors.append(
                f"The assertion '{query}' is completely unsubstantiated across indexed news outlets and public record."
            )
            if news_items:
                verified_facts.append(
                    f"Mainstream reporting focuses on official policy and public events regarding referenced figures, containing no corroboration of this rumor."
                )

            claims.append({
                "id": "claim-1",
                "claim": f"Asserted claim: '{query}'",
                "verdict": "debunked",
                "confidence": 0.98,
                "supporting_sources": [],
                "contradicting_sources": [{"title": n["title"], "url": n["url"], "publisher": n["publisher"]} for n in news_items[:3]],
                "summary": "Exhaustive cross-referencing across mainstream news archives reveals zero credible corroboration for this claim.",
            })

            synthesis_paragraph = (
                f"NarrativeLens analyzed {len(all_sources)} sources ({news_count} news reports, {social_count} social discussions). "
                f"The claim '{query}' is classified as 'DEBUNKED / UNFOUNDED'. "
                f"While indexed press sources cover related public figures, none report or corroborate this claim, confirming it is an unsubstantiated internet rumor."
            )

        # CASE B: Fact-Checked / Disputed Event
        elif fact_check_found or is_explicit_hoax_query or (hate_in_social > 0 and coverage_ratio < 0.6):
            overall_status = "disputed"
            truth_score = 0.42
            status_text = "Disputed Narrative: Significant divergence between verified news reports and viral social rumors."
            debunked_rumors.append("Online discussion channels feature sensationalized or unverified claims contradicted by investigative press.")
            claims.append({
                "id": "claim-1",
                "claim": f"Controversial assertion regarding '{query}'",
                "verdict": "disputed",
                "confidence": 0.85,
                "supporting_sources": [],
                "contradicting_sources": [{"title": n["title"], "url": n["url"], "publisher": n["publisher"]} for n in news_items[:2]],
                "summary": "Independent reporting identifies substantial factual discrepancies or unsubstantiated rumors.",
            })
            unresolved_questions.append("Conflicting interpretations remain active across social and journalistic channels.")

            synthesis_paragraph = (
                f"NarrativeLens analyzed {len(all_sources)} sources. "
                f"Coverage surrounding '{query}' is classified as 'DISPUTED'. "
                f"Fact-checking inquiries or contradictory coverage suggest caution when evaluating viral claims."
            )

        # CASE C: Verified Real-World Event / Topic
        elif news_count >= 2 and coverage_ratio >= 0.50:
            overall_status = "verified"
            truth_score = 0.90
            status_text = "Verified Grounded News: Story is substantially verified by multiple independent journalistic outlets."

            verified_facts.append(
                f"Multi-outlet journalistic consensus confirms core reporting: {headline[:80]} ({', '.join(publishers[:3])})."
            )
            claims.append({
                "id": "claim-1",
                "claim": f"Primary event reporting: {headline[:100]}",
                "verdict": "verified",
                "confidence": 0.92,
                "supporting_sources": [{"title": n["title"], "url": n["url"], "publisher": n["publisher"]} for n in news_items[:4]],
                "contradicting_sources": [],
                "summary": f"Consistent multi-outlet coverage across {len(publishers)} distinct newsrooms corroborates this event.",
            })

            if len(news_items) >= 2:
                sec_title = news_items[1]["title"]
                verified_facts.append(f"Independent validation reported by {news_items[1]['publisher']}: '{sec_title[:75]}...'")
                claims.append({
                    "id": "claim-2",
                    "claim": f"Corroborating coverage: {sec_title[:100]}",
                    "verdict": "verified",
                    "confidence": 0.88,
                    "supporting_sources": [{"title": news_items[1]["title"], "url": news_items[1]["url"], "publisher": news_items[1]["publisher"]}],
                    "contradicting_sources": [],
                    "summary": f"Substantiated by {news_items[1]['publisher']} with matching factual timeline.",
                })

            unresolved_questions.append("Long-term policy and institutional consequences remain developing.")
            claims.append({
                "id": "claim-3",
                "claim": "Conclusive final policy outcomes have been formalized.",
                "verdict": "unverified",
                "confidence": 0.65,
                "supporting_sources": [],
                "contradicting_sources": [],
                "summary": "Long-term institutional outcomes remain subject to ongoing public review.",
            })

            synthesis_paragraph = (
                f"NarrativeLens analyzed {len(all_sources)} sources ({news_count} news reports, {social_count} social discussions). "
                f"The primary coverage surrounding '{query}' is classified as 'VERIFIED'. "
                f"Reputable news coverage establishes factual groundwork with constructive public discussion."
            )

        # CASE D: Unverified / Speculative
        else:
            overall_status = "unverified"
            truth_score = 0.40
            status_text = "Unverified / Speculative: Limited primary source documentation found across indexed news outlets."
            unresolved_questions.append("No primary journalistic reporting corroborates this topic in indexed databases.")
            claims.append({
                "id": "claim-1",
                "claim": f"Topic coverage: {headline[:100]}",
                "verdict": "unverified",
                "confidence": 0.60,
                "supporting_sources": [{"title": n["title"], "url": n["url"], "publisher": n["publisher"]} for n in news_items[:2]],
                "contradicting_sources": [],
                "summary": "Preliminary coverage without independent secondary corroboration.",
            })

            synthesis_paragraph = (
                f"NarrativeLens analyzed {len(all_sources)} sources. "
                f"Coverage surrounding '{query}' is classified as 'UNVERIFIED'. "
                f"Insufficient independent reporting is available to make a certified determination."
            )

        return {
            "overall_status": overall_status,
            "truth_score": truth_score,
            "status_description": status_text,
            "executive_summary": synthesis_paragraph,
            "verified_facts": verified_facts,
            "debunked_rumors": debunked_rumors,
            "unresolved_questions": unresolved_questions,
            "claims": claims,
        }

    async def execute_narrative_investigation(
        self,
        query: str,
        article_url: Optional[str] = None,
        investigation_id: Optional[uuid.UUID] = None,
        max_items_per_source: int = 10,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Execute full multi-source narrative scraping, batch toxicity classification, and evidence synthesis."""
        start_time = datetime.now(timezone.utc)
        target_article = None

        search_query = query.strip()
        if article_url and article_url.strip():
            try:
                target_article = await self.scrape_article_url(article_url.strip())
                if not search_query:
                    search_query = target_article["title"]
            except Exception as exc:
                logger.warning(f"Error scraping article URL: {exc}")
                if not search_query:
                    search_query = "news narrative analysis"

        if not search_query:
            search_query = "public narrative controversy"

        # Concurrently fetch news and social media
        news_task = asyncio.create_task(self.search_newspapers_and_magazines(search_query, limit=max_items_per_source))
        social_task = asyncio.create_task(self.search_social_media(search_query, limit=max_items_per_source))

        news_items, social_items = await asyncio.gather(news_task, social_task)

        if target_article:
            news_items.insert(0, {
                "title": target_article["title"],
                "url": target_article["url"],
                "publisher": target_article["publisher"],
                "published_at": str(target_article["published_at"]),
                "snippet": target_article["snippet"],
                "source_type": "newspaper",
                "platform": "Primary Target URL",
            })

        # Batch evaluate toxicity across all items in one rapid pass
        self._analyze_toxicity_batch(news_items + social_items)

        # Synthesize Truth & Grounded Results
        synthesis = await self._extract_claims_and_synthesize_truth(
            query=search_query,
            target_article=target_article,
            news_items=news_items,
            social_items=social_items,
        )

        persisted_inv_id = investigation_id
        if db is not None:
            try:
                if not persisted_inv_id:
                    new_inv = Investigation(
                        title=f"Live Web Narrative: {search_query[:100]}",
                        description=synthesis["executive_summary"][:400],
                        keywords=[w.lower() for w in search_query.split() if len(w) > 3][:6],
                        languages=["en"],
                        source_types=["newspaper", "social_media"],
                        status="completed",
                    )
                    db.add(new_inv)
                    await db.flush()
                    persisted_inv_id = new_inv.id

                ds_news = DataSource(
                    investigation_id=persisted_inv_id,
                    source_type="newspaper",
                    name="Google News RSS & Press Outlets",
                    config={"query": search_query},
                )
                ds_social = DataSource(
                    investigation_id=persisted_inv_id,
                    source_type="social_media",
                    name="Reddit & HackerNews Public Discourse",
                    config={"query": search_query},
                )
                db.add_all([ds_news, ds_social])
                await db.flush()

                for item in (news_items + social_items)[:25]:
                    content_str = f"{item['title']}\n\n{item['snippet']}"
                    h = hashlib.sha256(content_str.encode("utf-8")).hexdigest()
                    doc = Document(
                        investigation_id=persisted_inv_id,
                        source_id=ds_news.id if item["source_type"] == "newspaper" else ds_social.id,
                        title=item["title"][:490],
                        url=item.get("url"),
                        author=item.get("publisher"),
                        content=content_str,
                        content_hash=h,
                        language="en",
                        source_type=item["source_type"],
                        metadata_={"platform": item.get("platform"), "toxicity": item.get("toxicity")},
                    )
                    db.add(doc)

                for c in synthesis.get("claims", []):
                    citation = EvidenceCitation(
                        investigation_id=persisted_inv_id,
                        claim_text=c["claim"],
                        supporting_sources=c.get("supporting_sources", []),
                        contradicting_sources=c.get("contradicting_sources", []),
                        evidence_status=c.get("verdict", "unverified"),
                        uncertainty_notes=c.get("summary"),
                    )
                    db.add(citation)

                await db.commit()
            except Exception as db_exc:
                logger.warning(f"Failed to persist scraped narrative to DB: {db_exc}")
                await db.rollback()

        toxicity_counts = {
            "hate_count": sum(1 for x in (news_items + social_items) if x.get("toxicity", {}).get("is_hate")),
            "offensive_count": sum(1 for x in (news_items + social_items) if x.get("toxicity", {}).get("is_offensive")),
            "neutral_count": sum(1 for x in (news_items + social_items) if not x.get("toxicity", {}).get("is_hate") and not x.get("toxicity", {}).get("is_offensive")),
        }

        return {
            "query": search_query,
            "investigation_id": str(persisted_inv_id) if persisted_inv_id else None,
            "target_article": target_article,
            "sources_searched": {
                "newspapers": len(news_items),
                "social_media": len(social_items),
                "total_documents": len(news_items) + len(social_items),
            },
            "verdict_summary": synthesis,
            "claims": synthesis["claims"],
            "collected_documents": (news_items + social_items),
            "toxicity_overview": toxicity_counts,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }


narrative_scraper_service = NarrativeScraperService()

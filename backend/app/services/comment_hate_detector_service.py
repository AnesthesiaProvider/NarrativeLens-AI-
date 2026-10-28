"""Service for scraping YouTube video titles and comment threads (as well as web articles),
detecting hate speech and toxic patterns, and generating actionable 'Need to Know' safety advisories."""

from __future__ import annotations

import asyncio
import logging
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.security import sanitize_html, sanitize_text, validate_url
from app.ml.model_manager import model_manager

try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 "
        "NarrativeLens-AI/1.0"
    )
}

YOUTUBE_URL_REGEX = re.compile(
    r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/|v\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})"
)


class CommentHateDetectorService:
    """Scrapes YouTube titles and comments, runs hate speech classification, and builds safety advisories."""

    def extract_youtube_video_id(self, target: str) -> Optional[str]:
        """Extract 11-char YouTube Video ID from URL or return if already a valid ID."""
        cleaned = target.strip()
        if re.fullmatch(r"[a-zA-Z0-9_-]{11}", cleaned):
            return cleaned
        match = YOUTUBE_URL_REGEX.search(cleaned)
        if match:
            return match.group(1)
        return None

    async def fetch_youtube_video_info(
        self, video_id: str, client: httpx.AsyncClient
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Fetch video title, channel, description, and top comments via YouTube Data API v3."""
        if not settings.YOUTUBE_API_KEY:
            raise ValueError(
                "YOUTUBE_API_KEY is not configured in backend/.env. Please provide a YouTube Data API v3 key."
            )

        video_meta: Dict[str, Any] = {
            "id": video_id,
            "title": "YouTube Video",
            "channel": "YouTube Creator",
            "description": "",
            "view_count": 0,
            "like_count": 0,
            "comment_count": 0,
            "url": f"https://www.youtube.com/watch?v={video_id}",
        }

        # 1. Fetch Video Metadata
        try:
            v_url = (
                f"https://www.googleapis.com/youtube/v3/videos"
                f"?part=snippet,statistics&id={video_id}&key={settings.YOUTUBE_API_KEY}"
            )
            resp = await client.get(v_url, timeout=12.0)
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                if items:
                    snippet = items[0].get("snippet", {})
                    stats = items[0].get("statistics", {})
                    video_meta.update({
                        "title": snippet.get("title", "YouTube Video"),
                        "channel": snippet.get("channelTitle", "YouTube Creator"),
                        "description": snippet.get("description", "")[:1000],
                        "published_at": snippet.get("publishedAt", ""),
                        "view_count": int(stats.get("viewCount", 0)),
                        "like_count": int(stats.get("likeCount", 0)),
                        "comment_count": int(stats.get("commentCount", 0)),
                    })
        except Exception as exc:
            logger.warning(f"Failed to fetch YouTube video metadata for {video_id}: {exc}")

        # 2. Fetch Top Comment Threads
        raw_comments: List[Dict[str, Any]] = []
        try:
            c_url = (
                f"https://www.googleapis.com/youtube/v3/commentThreads"
                f"?part=snippet&videoId={video_id}&maxResults=50&order=relevance&key={settings.YOUTUBE_API_KEY}"
            )
            c_resp = await client.get(c_url, timeout=12.0)
            if c_resp.status_code == 200:
                c_items = c_resp.json().get("items", [])
                for item in c_items:
                    top_snippet = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                    comment_text = top_snippet.get("textDisplay") or top_snippet.get("textOriginal", "")
                    clean_comment = sanitize_html(comment_text) if comment_text else ""
                    if clean_comment.strip():
                        raw_comments.append({
                            "id": item.get("id"),
                            "author": top_snippet.get("authorDisplayName", "Anonymous User"),
                            "author_avatar": top_snippet.get("authorProfileImageUrl", ""),
                            "text": clean_comment,
                            "like_count": int(top_snippet.get("likeCount", 0)),
                            "published_at": top_snippet.get("publishedAt", ""),
                        })
            elif c_resp.status_code == 403:
                err_data = c_resp.json().get("error", {})
                err_msg = err_data.get("message", "Comments disabled or quota reached")
                logger.warning(f"YouTube comments API forbidden for {video_id}: {err_msg}")
        except Exception as exc:
            logger.warning(f"Failed to fetch YouTube comments for {video_id}: {exc}")

        return video_meta, raw_comments

    async def search_and_fetch_youtube_topic(
        self, query: str, client: httpx.AsyncClient
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Search YouTube for a topic or narrative and fetch top video with its comments."""
        if not settings.YOUTUBE_API_KEY:
            raise ValueError("YOUTUBE_API_KEY is required to search and scrape YouTube comments.")

        encoded = urllib.parse.quote_plus(query)
        s_url = (
            f"https://www.googleapis.com/youtube/v3/search"
            f"?part=snippet&q={encoded}&type=video&maxResults=1&key={settings.YOUTUBE_API_KEY}"
        )
        resp = await client.get(s_url, timeout=12.0)
        if resp.status_code != 200:
            raise ValueError(f"YouTube search failed with HTTP {resp.status_code}: {resp.text[:150]}")

        items = resp.json().get("items", [])
        if not items:
            raise ValueError(f"No YouTube videos found matching query: '{query}'")

        video_id = items[0].get("id", {}).get("videoId")
        if not video_id:
            raise ValueError("Invalid YouTube video result from search.")

        return await self.fetch_youtube_video_info(video_id, client)

    async def scrape_web_article_and_paragraphs(
        self, url: str
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Scrape web article title and user comments/paragraphs when a website URL is provided."""
        is_safe, reason = validate_url(url)
        if not is_safe:
            raise ValueError(f"URL rejected by security policy: {reason}")

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=HEADERS) as client:
                resp = await client.get(url)
                if resp.status_code >= 400:
                    raise ValueError(f"Target article returned HTTP {resp.status_code}")
                raw_html = resp.text
        except Exception as exc:
            raise ValueError(f"Failed to fetch article from {url}: {exc}")

        title = ""
        paragraphs: List[str] = []

        if TRAFILATURA_AVAILABLE:
            try:
                extracted = trafilatura.bare_extraction(raw_html, url=url, with_metadata=True)
                if extracted:
                    title = extracted.title or ""
                    if extracted.text:
                        paragraphs = [p.strip() for p in extracted.text.split("\n\n") if len(p.strip()) > 30]
            except Exception:
                pass

        if not title or not paragraphs:
            soup = BeautifulSoup(raw_html, "html.parser")
            if not title:
                title = soup.title.string.strip() if soup.title and soup.title.string else "Web Article"
            if not paragraphs:
                for p in soup.find_all("p"):
                    pt = sanitize_text(p.get_text(strip=True))
                    if len(pt) > 30 and not any(
                        s in pt.lower() for s in ["cookie", "privacy", "terms", "subscribe"]
                    ):
                        paragraphs.append(pt)

        parsed_url = urllib.parse.urlparse(url)
        publisher = parsed_url.netloc.replace("www.", "")

        article_meta = {
            "id": url,
            "title": title or "Web Article",
            "channel": publisher,
            "description": "\n\n".join(paragraphs[:3]),
            "view_count": 0,
            "like_count": 0,
            "comment_count": len(paragraphs),
            "url": url,
        }

        comment_items = [
            {
                "id": str(i),
                "author": f"{publisher} Excerpt #{i+1}",
                "author_avatar": "",
                "text": p,
                "like_count": 0,
                "published_at": datetime.now(timezone.utc).isoformat(),
            }
            for i, p in enumerate(paragraphs[:40])
        ]

        return article_meta, comment_items

    def _classify_text(self, text: str) -> Dict[str, Any]:
        """Classify hate speech in a text segment with confidence and normalized labels."""
        if not text or not text.strip():
            return {
                "label": "Neutral",
                "raw_label": "normal",
                "confidence": 0.98,
                "is_hate": False,
                "is_offensive": False,
                "explanation_tokens": [],
            }

        try:
            pred = model_manager.predict_hate_speech(text[:512], explain=False)
            raw = pred.get("predicted_label", "normal").lower()
            conf = round(float(pred.get("confidence", 0.9)), 4)

            if raw in ("hate", "hatespeech", "hate_speech"):
                label = "Hate Speech"
                is_hate = True
                is_offensive = False
            elif raw in ("offensive", "toxic", "toxicity"):
                label = "Offensive"
                is_hate = False
                is_offensive = True
            else:
                label = "Neutral"
                is_hate = False
                is_offensive = False

            # Extract top contributing tokens for explainability (only for flagged items)
            tokens = []
            if is_hate or is_offensive:
                try:
                    exp_pred = model_manager.predict_hate_speech(text[:512], explain=True)
                    exp = exp_pred.get("explanation", {})
                    if isinstance(exp, dict):
                        features = exp.get("top_features") or exp.get("tokens") or []
                        for item in features[:5]:
                            if isinstance(item, dict):
                                token_str = item.get("token") or item.get("text", "")
                                score = item.get("score", 0.0)
                            else:
                                token_str = str(item)
                                score = 0.5
                            if token_str and not token_str.startswith("<") and not token_str.isspace():
                                tokens.append({"token": token_str.strip(), "score": round(float(score), 3)})
                except Exception:
                    pass

            return {
                "label": label,
                "raw_label": raw,
                "confidence": conf,
                "is_hate": is_hate,
                "is_offensive": is_offensive,
                "explanation_tokens": tokens,
            }
        except Exception as exc:
            logger.debug(f"Classification error: {exc}")
            return {
                "label": "Neutral",
                "raw_label": "normal",
                "confidence": 0.85,
                "is_hate": False,
                "is_offensive": False,
                "explanation_tokens": [],
            }

    async def explain_with_local_llm(
        self, context_title: str, text: str, initial_label: str, client: Optional[httpx.AsyncClient] = None
    ) -> Optional[Dict[str, Any]]:
        """Call local Ollama LLM (e.g. Qwen3-4B / LLaMA) to assess context, detect targeted groups, and provide deep analytical reasoning."""
        if not getattr(settings, "ENABLE_LLM_CONTEXT_ARBITER", True):
            return None

        base_url = getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        model_name = getattr(settings, "OLLAMA_MODEL", "qwen3:4b")
        req_timeout = float(getattr(settings, "OLLAMA_TIMEOUT", 25.0))

        prompt = (
            f"You are an expert NLP safety analyst evaluating user comments in context of online content.\n"
            f"Context / Video Title: \"{context_title}\"\n"
            f"User Comment: \"{text}\"\n"
            f"Initial Model Flag: {initial_label}\n\n"
            "Task: Conduct a deep analytical assessment on whether this is genuine hate speech (dehumanization, slurs, group incitement), "
            "offensive speech (profanity, aggressive personal insults), or neutral/free expression in context.\n"
            "Respond ONLY with valid JSON in this exact structure:\n"
            "{\n"
            "  \"verdict\": \"Hate Speech\" or \"Offensive\" or \"Neutral\",\n"
            "  \"targeted_group\": \"name of targeted group or None\",\n"
            "  \"explanation\": \"Deep analytical reasoning explaining the context, sarcasm, and linguistic intent.\"\n"
            "}"
        )

        try:
            req_payload = {
                "model": model_name,
                "prompt": prompt,
                "format": "json",
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 600},
            }
            if client:
                resp = await client.post(f"{base_url}/api/generate", json=req_payload, timeout=req_timeout)
            else:
                async with httpx.AsyncClient(timeout=req_timeout) as temp_client:
                    resp = await temp_client.post(f"{base_url}/api/generate", json=req_payload)

            if resp.status_code == 200:
                data = resp.json()
                raw_response = data.get("response", "").strip()
                raw_thinking = data.get("thinking", "").strip()

                import json
                import re

                parsed = {}
                # Try parsing response, then thinking, then regex extraction
                for candidate in (raw_response, raw_thinking):
                    if not candidate:
                        continue
                    try:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, dict) and "verdict" in parsed:
                            break
                    except Exception:
                        pass
                    # Regex search for JSON block
                    match = re.search(r"\{[\s\S]*?\}", candidate)
                    if match:
                        try:
                            candidate_obj = json.loads(match.group(0))
                            if isinstance(candidate_obj, dict) and "verdict" in candidate_obj:
                                parsed = candidate_obj
                                break
                        except Exception:
                            pass

                if parsed:
                    explanation = parsed.get("explanation", "").strip()
                    # If explanation was brief but thinking has rich analysis, use thinking if helpful
                    if not explanation and raw_thinking and not raw_thinking.startswith("{"):
                        explanation = raw_thinking[:400]

                    return {
                        "model": model_name,
                        "verdict": parsed.get("verdict", initial_label),
                        "targeted_group": parsed.get("targeted_group", "None"),
                        "explanation": explanation,
                        "analytical_depth": "deep_reasoning" if "qwen" in model_name.lower() else "standard",
                    }
        except Exception as exc:
            logger.debug(f"Ollama local LLM reasoning skipped ({exc})")

        return None

    async def analyze_target(
        self, target: str, max_comments: int = 50
    ) -> Dict[str, Any]:
        """Scrape video/article title and comments, detect hate speech, and generate 'Need to Know' advisory."""
        target = target.strip()
        if not target:
            raise ValueError("Target URL or search topic cannot be empty.")

        video_id = self.extract_youtube_video_id(target)

        async with httpx.AsyncClient(headers=HEADERS) as client:
            if video_id:
                meta, comments = await self.fetch_youtube_video_info(video_id, client)
            elif target.startswith("http://") or target.startswith("https://"):
                meta, comments = await self.scrape_web_article_and_paragraphs(target)
            else:
                # Treat as search query for YouTube
                meta, comments = await self.search_and_fetch_youtube_topic(target, client)

        # 1. Analyze Title for Hate Speech
        title_text = meta.get("title", "")
        title_eval = self._classify_text(title_text)

        # 2. Analyze Each Comment
        analyzed_comments: List[Dict[str, Any]] = []
        hate_count = 0
        offensive_count = 0
        neutral_count = 0

        for c in comments[:max_comments]:
            text = c.get("text", "")
            eval_res = self._classify_text(text)

            if eval_res["is_hate"]:
                hate_count += 1
            elif eval_res["is_offensive"]:
                offensive_count += 1
            else:
                neutral_count += 1

            analyzed_comments.append({
                "id": c.get("id"),
                "author": c.get("author"),
                "author_avatar": c.get("author_avatar"),
                "text": text,
                "like_count": c.get("like_count", 0),
                "published_at": c.get("published_at"),
                "label": eval_res["label"],
                "confidence": eval_res["confidence"],
                "is_hate": eval_res["is_hate"],
                "is_offensive": eval_res["is_offensive"],
                "explanation_tokens": eval_res["explanation_tokens"],
            })

        total_scanned = len(analyzed_comments)
        toxic_count = hate_count + offensive_count
        toxicity_rate = round((toxic_count / total_scanned), 4) if total_scanned > 0 else 0.0
        hate_rate = round((hate_count / total_scanned), 4) if total_scanned > 0 else 0.0

        # Sort flagged comments (hate speech first, then highest confidence, then likes)
        flagged_comments = [c for c in analyzed_comments if c["is_hate"] or c["is_offensive"]]
        flagged_comments.sort(
            key=lambda x: (1 if x["is_hate"] else 0, x["confidence"], x["like_count"]),
            reverse=True,
        )

        # 2b. Local LLM Contextual Arbitration (Ollama Llama 3.2 / Qwen 2.5)
        llm_active = False
        if title_eval["is_hate"] or title_eval["is_offensive"]:
            t_llm = await self.explain_with_local_llm(title_text, title_text, title_eval["label"])
            if t_llm:
                title_eval["llm_reasoning"] = t_llm
                llm_active = True

        async def _enrich_comment(c_item: Dict[str, Any]):
            llm_res = await self.explain_with_local_llm(title_text, c_item["text"], c_item["label"])
            if llm_res:
                c_item["llm_reasoning"] = llm_res
                return True
            return False

        if flagged_comments:
            enrich_tasks = [_enrich_comment(c) for c in flagged_comments[:5]]
            enrich_results = await asyncio.gather(*enrich_tasks, return_exceptions=True)
            if any(r is True for r in enrich_results if not isinstance(r, Exception)):
                llm_active = True

        # 3. Construct "Need to Know" Executive Safety & Narrative Advisory
        if hate_rate >= 0.20 or hate_count >= 5:
            risk_level = "CRITICAL_HARASSMENT"
            risk_label = "Critical Harassment & High Hate Density"
            color = "red"
        elif toxicity_rate >= 0.30 or hate_count >= 2:
            risk_level = "HIGH_TOXICITY"
            risk_label = "High Toxicity & Hostile Comments"
            color = "orange"
        elif toxicity_rate >= 0.12 or offensive_count >= 3:
            risk_level = "MODERATE_TENSION"
            risk_label = "Moderate Flaming / Divisive Rhetoric"
            color = "amber"
        else:
            risk_level = "LOW_RISK"
            risk_label = "Constructive / Low Risk Discussion"
            color = "emerald"

        # Key points someone needs to know
        need_to_know_advisories: List[str] = []

        if llm_active:
            need_to_know_advisories.append(
                f"🤖 Local LLM Context Arbiter Active ({getattr(settings, 'OLLAMA_MODEL', 'qwen3:4b')}): Contextual nuance, identity targeting, and intent analyzed via Ollama."
            )

        # Bullet 1: Title evaluation
        if title_eval["is_hate"]:
            need_to_know_advisories.append(
                f"🚨 WARNING: The headline/title itself was classified as HATE SPEECH ({title_eval['confidence']*100:.1f}% confidence). It actively spreads hostile or dehumanizing rhetoric."
            )
        elif title_eval["is_offensive"]:
            need_to_know_advisories.append(
                f"⚠️ CAUTION: The headline/title contains inflammatory or offensive framing ({title_eval['confidence']*100:.1f}% confidence), often designed as rage-bait."
            )
        else:
            need_to_know_advisories.append(
                "✅ Title Assessment: The title appears neutral and policy/factual in tone without explicit slurs or hate speech."
            )

        # Bullet 2: Community comment section sentiment
        if total_scanned == 0:
            need_to_know_advisories.append(
                "ℹ️ No public comments were available for this video (comments may be disabled or restricted by the channel creator)."
            )
        elif hate_count > 0:
            need_to_know_advisories.append(
                f"⚠️ Active Hate Speech Detected: {hate_count} comment(s) ({hate_rate*100:.1f}% of scanned) contain direct hate speech, targeting identity, protected characteristics, or group vilification."
            )
        else:
            need_to_know_advisories.append(
                "✅ Zero direct hate speech incidents detected in the scanned comment threads."
            )

        # Bullet 3: Overall hostility ratio
        if toxicity_rate > 0.25:
            need_to_know_advisories.append(
                f"🔥 High Hostility Index: {toxicity_rate*100:.1f}% of discussions exhibit severe trolling, abusive insults, or profanity."
            )
        elif toxicity_rate > 0.10:
            need_to_know_advisories.append(
                f"⚖️ Polarized Discourse: {toxicity_rate*100:.1f}% of discussion involves heated insults or aggressive disagreement."
            )
        elif total_scanned > 0:
            need_to_know_advisories.append(
                f"🌿 Healthy Dialogue: {neutral_count}/{total_scanned} comments ({neutral_count/total_scanned*100:.1f}%) remain civil and constructive."
            )

        # Bullet 4: Key high-impact flagged comment summary
        if flagged_comments:
            top_flagged = flagged_comments[0]
            need_to_know_advisories.append(
                f"📌 Most prominent flagged comment by @{top_flagged['author']} ({top_flagged['like_count']} likes): \"{top_flagged['text'][:120]}...\" — Flagged as {top_flagged['label']}."
            )

        return {
            "target": target,
            "target_type": "youtube" if video_id or "youtube.com" in target or "youtu.be" in target else "web_article",
            "metadata": meta,
            "title_analysis": {
                "text": title_text,
                "label": title_eval["label"],
                "confidence": title_eval["confidence"],
                "is_hate": title_eval["is_hate"],
                "is_offensive": title_eval["is_offensive"],
                "explanation_tokens": title_eval["explanation_tokens"],
                "llm_reasoning": title_eval.get("llm_reasoning"),
            },
            "metrics": {
                "total_scanned": total_scanned,
                "hate_count": hate_count,
                "offensive_count": offensive_count,
                "neutral_count": neutral_count,
                "toxic_count": toxic_count,
                "toxicity_rate": toxicity_rate,
                "hate_rate": hate_rate,
            },
            "advisory": {
                "risk_level": risk_level,
                "risk_label": risk_label,
                "risk_color": color,
                "llm_active": llm_active,
                "llm_model": getattr(settings, "OLLAMA_MODEL", "qwen3:4b") if llm_active else None,
                "what_you_need_to_know": need_to_know_advisories,
            },
            "flagged_comments": flagged_comments,
            "all_comments": analyzed_comments,
            "scanned_at": datetime.now(timezone.utc).isoformat(),
        }


comment_hate_detector_service = CommentHateDetectorService()

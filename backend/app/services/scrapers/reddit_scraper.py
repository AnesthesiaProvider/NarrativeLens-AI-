"""Reddit scraper with dual-mode support: PRAW (authenticated) + public JSON API (zero credentials).

Handles Reddit threads, subreddits, and keyword searches. When PRAW credentials
(REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET) are absent, it automatically uses
Reddit's public JSON endpoints with custom User-Agent headers.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from bs4 import BeautifulSoup

from app.core.config import settings
from .base import BaseScraper, ScrapedContent, StandardDocument
from .rate_limiter import rate_limiter

logger = logging.getLogger(__name__)

REDDIT_SUBMISSION_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.|old\.|new\.)?reddit\.com/r/(?P<subpop>[^/]+)/comments/(?P<id>[a-zA-Z0-9]+)",
    re.IGNORECASE,
)
REDDIT_SHORT_PATTERN = re.compile(r"(?:https?://)?redd\.it/(?P<id>[a-zA-Z0-9]+)", re.IGNORECASE)
SUBREDDIT_PATTERN = re.compile(
    r"^(?:https?://)?(?:www\.|old\.|new\.)?reddit\.com/r/(?P<sub>[a-zA-Z0-9_]+)/?(?:(?:hot|new|top|rising)/?)?$",
    re.IGNORECASE,
)
SHORTHAND_SUBREDDIT = re.compile(r"^/?r/(?P<sub>[a-zA-Z0-9_]+)/?$", re.IGNORECASE)

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


class RedditScraper(BaseScraper):
    """Scrapes Reddit threads, subreddits, and search queries."""

    PLATFORM_NAME = "reddit"

    HEADERS = {
        "User-Agent": (
            getattr(settings, "REDDIT_USER_AGENT", None)
            or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) NarrativeLens-AI/1.0"
        ),
        "Accept": "application/json",
    }

    def __init__(self):
        super().__init__()
        self._praw_instance = None
        self._praw_attempted = False

    def can_handle(self, target: str) -> bool:
        """Check if target represents a Reddit URL or subreddit shorthand."""
        t = target.strip()
        if "reddit.com" in t or "redd.it" in t:
            return True
        if t.startswith("r/") or t.startswith("/r/"):
            return True
        return False

    def _get_praw(self):
        """Lazy initialization of PRAW instance if credentials exist."""
        if self._praw_attempted:
            return self._praw_instance

        self._praw_attempted = True
        client_id = getattr(settings, "REDDIT_CLIENT_ID", None)
        client_secret = getattr(settings, "REDDIT_CLIENT_SECRET", None)

        if client_id and client_secret:
            try:
                import praw
                self._praw_instance = praw.Reddit(
                    client_id=client_id,
                    client_secret=client_secret,
                    user_agent=getattr(settings, "REDDIT_USER_AGENT", "NarrativeLens:v1.0"),
                )
                self._praw_instance.read_only = True
                logger.info("Reddit PRAW initialized successfully in read-only mode.")
            except Exception as exc:
                logger.warning(f"Failed to initialize PRAW: {exc}. Will fallback to public JSON API.")
        else:
            logger.info("Reddit API credentials not configured; using public JSON fallback.")

        return self._praw_instance

    def _extract_image_url(self, post_data: Dict[str, Any]) -> Optional[str]:
        """Extract high-res image URL from reddit post dictionary."""
        url = post_data.get("url", "")
        if any(url.lower().endswith(ext) for ext in IMAGE_EXTENSIONS):
            return url
        if "i.redd.it" in url or "i.imgur.com" in url:
            return url
        return None

    async def _download_image(self, client: httpx.AsyncClient, url: str) -> Optional[bytes]:
        """Safely fetch image bytes for multimodal CLIP processing."""
        try:
            resp = await client.get(url, timeout=7.0)
            if resp.status_code == 200 and len(resp.content) <= 8 * 1024 * 1024:
                return resp.content
        except Exception:
            pass
        return None

    async def scrape(
        self,
        target: str,
        max_items: int = 50,
        download_images: bool = True,
        max_images: int = 3,
        **kwargs,
    ) -> ScrapedContent:
        """Scrape reddit target. Dispatches to PRAW if configured, else public JSON."""
        praw = self._get_praw()
        if praw:
            try:
                return await asyncio.to_thread(
                    self._scrape_with_praw, praw, target, max_items, download_images, max_images
                )
            except Exception as exc:
                logger.warning(f"PRAW scrape failed: {exc}. Retrying with public JSON fallback.")

        # Fallback to public JSON endpoints
        return await self._scrape_with_json(target, max_items, download_images, max_images)

    # -----------------------------------------------------------------------
    # Public JSON Scraper (Zero credentials)
    # -----------------------------------------------------------------------

    async def _scrape_with_json(
        self,
        target: str,
        max_items: int,
        download_images: bool,
        max_images: int,
    ) -> ScrapedContent:
        """Fetch reddit content using the public .json URL pattern."""
        t = target.strip()
        await rate_limiter.wait("reddit")

        # Determine target type and clean URL
        m_sub = REDDIT_SUBMISSION_PATTERN.search(t)
        m_short = REDDIT_SHORT_PATTERN.search(t)
        m_subreddit = SUBREDDIT_PATTERN.search(t)
        m_shorthand = SHORTHAND_SUBREDDIT.search(t)

        async with httpx.AsyncClient(headers=self.HEADERS, follow_redirects=True) as client:
            if m_sub or m_short:
                return await self._scrape_json_thread(client, t, max_items, download_images, max_images)
            elif m_subreddit or m_shorthand:
                sub_name = (m_subreddit.group("sub") if m_subreddit else m_shorthand.group("sub"))
                return await self._scrape_json_subreddit(client, sub_name, max_items, download_images, max_images)
            else:
                # Treat as search query or general URL
                clean_target = t.rstrip("/")
                if not clean_target.endswith(".json"):
                    clean_target += ".json"
                try:
                    resp = await client.get(clean_target, timeout=12.0)
                    if resp.status_code == 200:
                        return await self._parse_json_generic(client, resp.json(), target, max_items, download_images, max_images)
                except Exception as exc:
                    return ScrapedContent(
                        platform=self.PLATFORM_NAME,
                        target=target,
                        target_type="unknown",
                        errors=[f"Could not parse Reddit target with JSON fallback: {exc}"],
                    )

        return ScrapedContent(
            platform=self.PLATFORM_NAME,
            target=target,
            target_type="unknown",
            errors=[f"Unsupported Reddit target format: {target}"],
        )

    async def _scrape_json_thread(
        self,
        client: httpx.AsyncClient,
        url: str,
        max_items: int,
        download_images: bool,
        max_images: int,
    ) -> ScrapedContent:
        """Fetch single thread and comments via .json."""
        clean_url = url.split("?")[0].rstrip("/")
        if not clean_url.endswith(".json"):
            clean_url += ".json"

        try:
            resp = await client.get(clean_url, timeout=12.0)
            if resp.status_code == 404:
                return ScrapedContent(
                    platform=self.PLATFORM_NAME,
                    target=url,
                    target_type="thread",
                    errors=["Reddit post not found or removed (404)."],
                )
            if resp.status_code in (403, 429):
                logger.info(f"Reddit thread JSON returned HTTP {resp.status_code}. Falling back to public RSS stream.")
                return await self._scrape_rss_thread(client, url, max_items)
            if resp.status_code != 200:
                logger.info(f"Reddit thread JSON returned HTTP {resp.status_code}. Trying RSS fallback.")
                rss_res = await self._scrape_rss_thread(client, url, max_items)
                if rss_res.documents or rss_res.main_document:
                    return rss_res
                return ScrapedContent(
                    platform=self.PLATFORM_NAME,
                    target=url,
                    target_type="thread",
                    errors=[f"Reddit returned HTTP {resp.status_code}"],
                )
            data = resp.json()
        except Exception as exc:
            logger.info(f"Failed to fetch thread JSON: {exc}. Trying RSS fallback.")
            rss_res = await self._scrape_rss_thread(client, url, max_items)
            if rss_res.documents or rss_res.main_document:
                return rss_res
            return ScrapedContent(
                platform=self.PLATFORM_NAME,
                target=url,
                target_type="thread",
                errors=[f"Failed to fetch thread JSON: {exc}"],
            )

        if not isinstance(data, list) or len(data) < 2:
            return ScrapedContent(
                platform=self.PLATFORM_NAME,
                target=url,
                target_type="thread",
                errors=["Unexpected Reddit JSON structure."],
            )

        # 1. Post (OP)
        post_listing = data[0].get("data", {}).get("children", [])
        if not post_listing:
            return ScrapedContent(platform=self.PLATFORM_NAME, target=url, target_type="thread", errors=["Empty post children."])

        op_data = post_listing[0].get("data", {})
        title = op_data.get("title", "")
        selftext = op_data.get("selftext", "")
        author = op_data.get("author", "[deleted]")
        subreddit = op_data.get("subreddit", "")
        permalink = f"https://reddit.com{op_data.get('permalink', '')}"
        created_utc = op_data.get("created_utc")
        pub_dt = datetime.fromtimestamp(created_utc, tz=timezone.utc) if created_utc else None

        img_url = self._extract_image_url(op_data)
        img_bytes_list = []
        img_urls = [img_url] if img_url else []
        if img_url and download_images:
            b = await self._download_image(client, img_url)
            if b:
                img_bytes_list.append(b)

        main_doc = StandardDocument(
            source_platform=self.PLATFORM_NAME,
            source_url=permalink,
            doc_type="post",
            title=title,
            text=selftext,
            author=author,
            image_urls=img_urls,
            image_bytes_list=img_bytes_list,
            score=op_data.get("score", 0),
            reply_count=op_data.get("num_comments", 0),
            published_at=pub_dt,
            subreddit=subreddit,
            thread_id=op_data.get("id", ""),
            doc_id=f"reddit-{op_data.get('id', '')}",
        )

        # 2. Comments
        comment_listing = data[1].get("data", {}).get("children", [])
        comment_docs: List[StandardDocument] = []

        def extract_comments_recursive(children: List[Dict[str, Any]]):
            for child in children:
                if len(comment_docs) >= max_items:
                    return
                c_data = child.get("data", {})
                body = c_data.get("body", "")
                if not body or body in ("[deleted]", "[removed]"):
                    continue

                c_author = c_data.get("author", "[deleted]")
                c_utc = c_data.get("created_utc")
                c_dt = datetime.fromtimestamp(c_utc, tz=timezone.utc) if c_utc else None
                c_id = c_data.get("id", "")

                doc = StandardDocument(
                    source_platform=self.PLATFORM_NAME,
                    source_url=f"https://reddit.com{c_data.get('permalink', '')}",
                    doc_type="comment",
                    text=body,
                    author=c_author,
                    score=c_data.get("score", 0),
                    published_at=c_dt,
                    subreddit=subreddit,
                    thread_id=op_data.get("id", ""),
                    parent_id=c_data.get("parent_id", ""),
                    doc_id=f"reddit-c-{c_id}",
                )
                comment_docs.append(doc)

                # Nested replies
                replies = c_data.get("replies")
                if isinstance(replies, dict):
                    nested = replies.get("data", {}).get("children", [])
                    extract_comments_recursive(nested)

        extract_comments_recursive(comment_listing)

        return ScrapedContent(
            platform=self.PLATFORM_NAME,
            target=url,
            target_type="thread",
            main_document=main_doc,
            documents=comment_docs,
            total_scraped=1 + len(comment_docs),
            source_metadata={
                "subreddit": subreddit,
                "title": title,
                "author": author,
                "score": op_data.get("score", 0),
                "total_comments_in_thread": op_data.get("num_comments", 0),
            },
        )

    async def _scrape_json_subreddit(
        self,
        client: httpx.AsyncClient,
        subreddit: str,
        max_items: int,
        download_images: bool,
        max_images: int,
    ) -> ScrapedContent:
        """Fetch hot posts from a subreddit via .json."""
        api_url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={min(max_items, 100)}"

        try:
            resp = await client.get(api_url, timeout=12.0)
            if resp.status_code in (403, 429):
                logger.info(f"Subreddit r/{subreddit} JSON returned HTTP {resp.status_code}. Falling back to public RSS.")
                return await self._scrape_rss_subreddit(client, subreddit, max_items, download_images, max_images)
            if resp.status_code != 200:
                logger.info(f"Subreddit r/{subreddit} JSON returned HTTP {resp.status_code}. Trying RSS fallback.")
                rss_res = await self._scrape_rss_subreddit(client, subreddit, max_items, download_images, max_images)
                if rss_res.documents:
                    return rss_res
                return ScrapedContent(
                    platform=self.PLATFORM_NAME,
                    target=f"r/{subreddit}",
                    target_type="subreddit",
                    errors=[f"Subreddit r/{subreddit} query returned HTTP {resp.status_code}"],
                )
            data = resp.json()
        except Exception as exc:
            logger.info(f"Failed to fetch subreddit JSON: {exc}. Trying RSS fallback.")
            rss_res = await self._scrape_rss_subreddit(client, subreddit, max_items, download_images, max_images)
            if rss_res.documents:
                return rss_res
            return ScrapedContent(
                platform=self.PLATFORM_NAME,
                target=f"r/{subreddit}",
                target_type="subreddit",
                errors=[f"Failed to fetch subreddit: {exc}"],
            )

        children = data.get("data", {}).get("children", [])
        docs: List[StandardDocument] = []
        img_count = 0

        for child in children[:max_items]:
            p = child.get("data", {})
            title = p.get("title", "")
            selftext = p.get("selftext", "")
            utc = p.get("created_utc")
            pub_dt = datetime.fromtimestamp(utc, tz=timezone.utc) if utc else None

            img_url = self._extract_image_url(p)
            img_urls = [img_url] if img_url else []
            img_bytes_list = []
            if img_url and download_images and img_count < max_images:
                b = await self._download_image(client, img_url)
                if b:
                    img_bytes_list.append(b)
                    img_count += 1

            doc = StandardDocument(
                source_platform=self.PLATFORM_NAME,
                source_url=f"https://reddit.com{p.get('permalink', '')}",
                doc_type="post",
                title=title,
                text=selftext or title,
                author=p.get("author", "[deleted]"),
                image_urls=img_urls,
                image_bytes_list=img_bytes_list,
                score=p.get("score", 0),
                reply_count=p.get("num_comments", 0),
                published_at=pub_dt,
                subreddit=subreddit,
                thread_id=p.get("id", ""),
                doc_id=f"reddit-{p.get('id', '')}",
            )
            docs.append(doc)

        return ScrapedContent(
            platform=self.PLATFORM_NAME,
            target=f"https://reddit.com/r/{subreddit}",
            target_type="subreddit",
            documents=docs,
            total_scraped=len(docs),
            source_metadata={
                "subreddit": subreddit,
                "title": f"r/{subreddit} (Hot)",
                "posts_count": len(docs),
            },
        )

    async def _scrape_rss_subreddit(
        self,
        client: httpx.AsyncClient,
        subreddit: str,
        max_items: int,
        download_images: bool,
        max_images: int,
    ) -> ScrapedContent:
        """Fallback to Reddit's public RSS feed when JSON endpoints are blocked."""
        rss_url = f"https://www.reddit.com/r/{subreddit}/.rss"
        try:
            import feedparser
            resp = await client.get(rss_url, timeout=12.0)
            if resp.status_code == 200:
                feed = feedparser.parse(resp.text)
                docs: List[StandardDocument] = []
                for entry in feed.entries[:max_items]:
                    e_title = entry.get("title", "")
                    e_author = entry.get("author", "[deleted]").replace("/u/", "")
                    e_link = entry.get("link", "")
                    summary_html = entry.get("summary", "")
                    text = e_title
                    if summary_html:
                        soup = BeautifulSoup(summary_html, "html.parser")
                        text_parts = [p.get_text(strip=True) for p in soup.find_all("p")]
                        if text_parts:
                            text = f"{e_title}\n" + " ".join(text_parts)

                    docs.append(
                        StandardDocument(
                            source_platform=self.PLATFORM_NAME,
                            source_url=e_link,
                            doc_type="post",
                            title=e_title,
                            text=text,
                            author=e_author,
                            subreddit=subreddit,
                            doc_id=f"reddit-rss-{hash(e_link) & 0xFFFFFFFF:x}",
                        )
                    )
                if docs:
                    return ScrapedContent(
                        platform=self.PLATFORM_NAME,
                        target=f"r/{subreddit}",
                        target_type="subreddit",
                        documents=docs,
                        total_scraped=len(docs),
                        source_metadata={
                            "subreddit": subreddit,
                            "source": "Reddit Public RSS (Verified Fallback)",
                        },
                    )
        except Exception as exc:
            logger.debug(f"Reddit RSS subreddit fallback failed: {exc}")

        return ScrapedContent(
            platform=self.PLATFORM_NAME,
            target=f"r/{subreddit}",
            target_type="subreddit",
            errors=[
                f"Subreddit r/{subreddit} returned HTTP 403 Forbidden. "
                "Reddit blocks anonymous unauthenticated requests. "
                "Please configure free Reddit credentials at https://www.reddit.com/prefs/apps and add "
                "REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET to your backend/.env file."
            ],
        )

    async def _scrape_rss_thread(
        self,
        client: httpx.AsyncClient,
        url: str,
        max_items: int,
    ) -> ScrapedContent:
        """Fallback to Reddit's thread RSS feed when JSON endpoints are blocked."""
        clean_url = url.rstrip("/")
        if clean_url.endswith(".json"):
            clean_url = clean_url[:-5]
        rss_url = f"{clean_url}/.rss"
        try:
            import feedparser
            resp = await client.get(rss_url, timeout=12.0)
            if resp.status_code == 200:
                feed = feedparser.parse(resp.text)
                if feed.entries:
                    op = feed.entries[0]
                    op_title = op.get("title", "")
                    op_author = op.get("author", "[deleted]").replace("/u/", "")
                    op_link = op.get("link", clean_url)

                    main_doc = StandardDocument(
                        source_platform=self.PLATFORM_NAME,
                        source_url=op_link,
                        doc_type="post",
                        title=op_title,
                        text=op_title,
                        author=op_author,
                        doc_id=f"reddit-rss-op-{hash(op_link) & 0xFFFFFFFF:x}",
                    )

                    comment_docs: List[StandardDocument] = []
                    for entry in feed.entries[1:max_items + 1]:
                        c_title = entry.get("title", "")
                        c_author = entry.get("author", "[deleted]").replace("/u/", "")
                        c_link = entry.get("link", "")
                        summary_html = entry.get("summary", "")
                        c_text = c_title
                        if summary_html:
                            soup = BeautifulSoup(summary_html, "html.parser")
                            body_parts = [p.get_text(strip=True) for p in soup.find_all("p")]
                            if body_parts:
                                c_text = " ".join(body_parts)

                        comment_docs.append(
                            StandardDocument(
                                source_platform=self.PLATFORM_NAME,
                                source_url=c_link,
                                doc_type="comment",
                                text=c_text,
                                author=c_author,
                                doc_id=f"reddit-rss-c-{hash(c_link) & 0xFFFFFFFF:x}",
                            )
                        )
                    return ScrapedContent(
                        platform=self.PLATFORM_NAME,
                        target=url,
                        target_type="thread",
                        main_document=main_doc,
                        documents=comment_docs,
                        total_scraped=1 + len(comment_docs),
                        source_metadata={
                            "title": op_title,
                            "author": op_author,
                            "source": "Reddit Public RSS (Verified Fallback)",
                        },
                    )
        except Exception as exc:
            logger.debug(f"Reddit RSS thread fallback failed: {exc}")

        return ScrapedContent(
            platform=self.PLATFORM_NAME,
            target=url,
            target_type="thread",
            errors=[
                "Reddit returned HTTP 403 Forbidden. Reddit blocks anonymous unauthenticated requests. "
                "Please configure free Reddit credentials at https://www.reddit.com/prefs/apps and add "
                "REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET to your backend/.env file."
            ],
        )

    async def _parse_json_generic(
        self,
        client: httpx.AsyncClient,
        data: Any,
        target: str,
        max_items: int,
        download_images: bool,
        max_images: int,
    ) -> ScrapedContent:
        """Generic parser for search results or listing data."""
        if not isinstance(data, dict):
            return ScrapedContent(platform=self.PLATFORM_NAME, target=target, target_type="generic", errors=["Invalid JSON root"])

        children = data.get("data", {}).get("children", [])
        docs = []
        for child in children[:max_items]:
            p = child.get("data", {})
            title = p.get("title", "")
            text = p.get("selftext", "") or p.get("body", "") or title
            doc = StandardDocument(
                source_platform=self.PLATFORM_NAME,
                source_url=f"https://reddit.com{p.get('permalink', '')}",
                doc_type=child.get("kind", "t3"),
                title=title,
                text=text,
                author=p.get("author", "[deleted]"),
                score=p.get("score", 0),
                subreddit=p.get("subreddit", ""),
                doc_id=f"reddit-{p.get('id', '')}",
            )
            docs.append(doc)

        return ScrapedContent(
            platform=self.PLATFORM_NAME,
            target=target,
            target_type="generic_listing",
            documents=docs,
            total_scraped=len(docs),
        )

    # -----------------------------------------------------------------------
    # PRAW Implementation (Synchronous, called via asyncio.to_thread)
    # -----------------------------------------------------------------------

    def _scrape_with_praw(
        self,
        praw_instance,
        target: str,
        max_items: int,
        download_images: bool,
        max_images: int,
    ) -> ScrapedContent:
        """Scrape Reddit via authenticated PRAW client."""
        t = target.strip()

        # Check if submission URL
        if "comments" in t or "redd.it" in t:
            submission = praw_instance.submission(url=t)
            op_title = submission.title
            op_text = submission.selftext
            op_author = str(submission.author) if submission.author else "[deleted]"
            subreddit = str(submission.subreddit)
            permalink = f"https://reddit.com{submission.permalink}"
            pub_dt = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)

            img_urls = []
            if any(submission.url.lower().endswith(ext) for ext in IMAGE_EXTENSIONS):
                img_urls.append(submission.url)

            main_doc = StandardDocument(
                source_platform=self.PLATFORM_NAME,
                source_url=permalink,
                doc_type="post",
                title=op_title,
                text=op_text,
                author=op_author,
                image_urls=img_urls,
                score=submission.score,
                reply_count=submission.num_comments,
                published_at=pub_dt,
                subreddit=subreddit,
                thread_id=submission.id,
                doc_id=f"reddit-{submission.id}",
            )

            # Flatten comments
            submission.comments.replace_more(limit=0)
            comment_docs = []
            for c in submission.comments.list()[:max_items]:
                body = c.body
                if not body or body in ("[deleted]", "[removed]"):
                    continue
                c_author = str(c.author) if c.author else "[deleted]"
                c_dt = datetime.fromtimestamp(c.created_utc, tz=timezone.utc)

                doc = StandardDocument(
                    source_platform=self.PLATFORM_NAME,
                    source_url=f"https://reddit.com{c.permalink}",
                    doc_type="comment",
                    text=body,
                    author=c_author,
                    score=c.score,
                    published_at=c_dt,
                    subreddit=subreddit,
                    thread_id=submission.id,
                    parent_id=c.parent_id,
                    doc_id=f"reddit-c-{c.id}",
                )
                comment_docs.append(doc)

            return ScrapedContent(
                platform=self.PLATFORM_NAME,
                target=target,
                target_type="thread",
                main_document=main_doc,
                documents=comment_docs,
                total_scraped=1 + len(comment_docs),
                source_metadata={
                    "subreddit": subreddit,
                    "title": op_title,
                    "author": op_author,
                    "score": submission.score,
                },
            )
        else:
            # Subreddit
            sub_name = t.replace("https://reddit.com/r/", "").replace("r/", "").strip("/")
            sub = praw_instance.subreddit(sub_name)
            docs = []
            for post in sub.hot(limit=max_items):
                docs.append(
                    StandardDocument(
                        source_platform=self.PLATFORM_NAME,
                        source_url=f"https://reddit.com{post.permalink}",
                        doc_type="post",
                        title=post.title,
                        text=post.selftext or post.title,
                        author=str(post.author) if post.author else "[deleted]",
                        score=post.score,
                        reply_count=post.num_comments,
                        published_at=datetime.fromtimestamp(post.created_utc, tz=timezone.utc),
                        subreddit=sub_name,
                        thread_id=post.id,
                        doc_id=f"reddit-{post.id}",
                    )
                )

            return ScrapedContent(
                platform=self.PLATFORM_NAME,
                target=target,
                target_type="subreddit",
                documents=docs,
                total_scraped=len(docs),
                source_metadata={"subreddit": sub_name, "title": f"r/{sub_name}"},
            )

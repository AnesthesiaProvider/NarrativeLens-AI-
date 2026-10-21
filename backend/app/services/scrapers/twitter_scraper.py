"""Twitter / X scraper with snscrape and public Nitter mirror fallbacks.

Scrapes public tweets, replies, user timelines, and hashtag searches.
Runs without requiring paid Twitter Developer API keys.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

from .base import BaseScraper, ScrapedContent, StandardDocument
from .rate_limiter import rate_limiter

logger = logging.getLogger(__name__)

TWITTER_URL_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com|nitter\.\w+)/(?P<user>[a-zA-Z0-9_]+)(?:/status/(?P<tweet_id>\d+))?",
    re.IGNORECASE,
)
HASHTAG_PATTERN = re.compile(r"^#?(?P<tag>[a-zA-Z0-9_]+)$")

NITTER_MIRRORS = [
    "https://nitter.net",
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
]


class TwitterScraper(BaseScraper):
    """Scraper for Twitter / X via snscrape with Nitter fallbacks."""

    PLATFORM_NAME = "twitter"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
    }

    def can_handle(self, target: str) -> bool:
        """Check if target is a Twitter/X URL or hashtag."""
        t = target.strip()
        if "twitter.com" in t or "x.com" in t or "nitter." in t:
            return True
        if t.startswith("#"):
            return True
        return False

    async def scrape(
        self,
        target: str,
        max_items: int = 50,
        download_images: bool = True,
        max_images: int = 2,
        **kwargs,
    ) -> ScrapedContent:
        """Scrape tweets. Tries snscrape first, then Nitter web fallback."""
        await rate_limiter.wait("twitter")

        # Try snscrape in worker thread
        try:
            res = await asyncio.to_thread(self._scrape_with_snscrape, target, max_items)
            if res.documents or res.main_document:
                return res
        except Exception as exc:
            logger.warning(f"snscrape failed for '{target}': {exc}. Trying Nitter fallback.")

        # Fallback to public Nitter mirror
        return await self._scrape_with_nitter(target, max_items)

    def _scrape_with_snscrape(self, target: str, max_items: int) -> ScrapedContent:
        """Synchronous snscrape execution."""
        import snscrape.modules.twitter as sntwitter

        t = target.strip()
        m = TWITTER_URL_PATTERN.search(t)

        docs: List[StandardDocument] = []
        main_doc: Optional[StandardDocument] = None

        if m and m.group("tweet_id"):
            # Single Tweet + conversation
            tweet_id = int(m.group("tweet_id"))
            scraper = sntwitter.TwitterTweetScraper(tweet_id)
            for i, tweet in enumerate(scraper.get_items()):
                if i >= max_items:
                    break
                doc = self._tweet_to_doc(tweet)
                if i == 0:
                    main_doc = doc
                else:
                    docs.append(doc)

            return ScrapedContent(
                platform=self.PLATFORM_NAME,
                target=target,
                target_type="tweet_thread",
                main_document=main_doc,
                documents=docs,
                total_scraped=(1 if main_doc else 0) + len(docs),
                source_metadata={
                    "tweet_id": tweet_id,
                    "author": main_doc.author if main_doc else "Unknown",
                },
            )

        elif m and m.group("user") and not t.startswith("#"):
            # User profile / timeline
            username = m.group("user")
            scraper = sntwitter.TwitterUserScraper(username)
            for i, tweet in enumerate(scraper.get_items()):
                if i >= max_items:
                    break
                docs.append(self._tweet_to_doc(tweet))

            return ScrapedContent(
                platform=self.PLATFORM_NAME,
                target=target,
                target_type="user_timeline",
                documents=docs,
                total_scraped=len(docs),
                source_metadata={"username": username, "tweets_found": len(docs)},
            )
        else:
            # Query / Hashtag
            query = t if not t.startswith("#") else t
            scraper = sntwitter.TwitterSearchScraper(query)
            for i, tweet in enumerate(scraper.get_items()):
                if i >= max_items:
                    break
                docs.append(self._tweet_to_doc(tweet))

            return ScrapedContent(
                platform=self.PLATFORM_NAME,
                target=target,
                target_type="search_query",
                documents=docs,
                total_scraped=len(docs),
                source_metadata={"query": query, "tweets_found": len(docs)},
            )

    def _tweet_to_doc(self, tweet: Any) -> StandardDocument:
        """Convert an snscrape tweet object into a StandardDocument."""
        text = getattr(tweet, "rawContent", "") or getattr(tweet, "content", "")
        author_user = getattr(tweet, "user", None)
        author_name = getattr(author_user, "username", "Anonymous") if author_user else "Anonymous"

        media = getattr(tweet, "media", []) or []
        img_urls = []
        for item in media:
            full_url = getattr(item, "fullUrl", None) or getattr(item, "previewUrl", None)
            if full_url:
                img_urls.append(full_url)

        like_count = getattr(tweet, "likeCount", 0) or 0
        retweet_count = getattr(tweet, "retweetCount", 0) or 0
        reply_count = getattr(tweet, "replyCount", 0) or 0
        date = getattr(tweet, "date", None)
        hashtags = getattr(tweet, "hashtags", []) or []

        return StandardDocument(
            source_platform=self.PLATFORM_NAME,
            source_url=getattr(tweet, "url", ""),
            doc_type="post",
            text=text,
            author=author_name,
            score=like_count + retweet_count,
            reply_count=reply_count,
            published_at=date,
            hashtags=[str(h) for h in hashtags if h],
            image_urls=img_urls,
            thread_id=str(getattr(tweet, "conversationId", "") or ""),
            doc_id=f"twitter-{getattr(tweet, 'id', '')}",
        )

    async def _scrape_with_nitter(self, target: str, max_items: int) -> ScrapedContent:
        """Scrape via public Nitter instance HTML when snscrape is blocked."""
        t = target.strip()
        m = TWITTER_URL_PATTERN.search(t)

        path = ""
        if m and m.group("user"):
            if m.group("tweet_id"):
                path = f"/{m.group('user')}/status/{m.group('tweet_id')}"
            else:
                path = f"/{m.group('user')}"
        elif t.startswith("#"):
            path = f"/search?f=tweets&q=%23{t.lstrip('#')}"
        else:
            path = f"/search?f=tweets&q={t}"

        errors = []
        for mirror in NITTER_MIRRORS:
            nitter_url = f"{mirror}{path}"
            try:
                async with httpx.AsyncClient(headers=self.HEADERS, timeout=10.0, follow_redirects=True) as client:
                    resp = await client.get(nitter_url)
                    if resp.status_code == 200:
                        return self._parse_nitter_html(resp.text, nitter_url, max_items)
            except Exception as exc:
                errors.append(f"{mirror}: {exc}")

        return ScrapedContent(
            platform=self.PLATFORM_NAME,
            target=target,
            target_type="twitter",
            errors=[f"All Twitter scraping methods failed (snscrape & Nitter mirrors): {errors}"],
        )

    def _parse_nitter_html(self, html: str, source_url: str, max_items: int) -> ScrapedContent:
        """Parse Nitter HTML output into StandardDocument instances."""
        soup = BeautifulSoup(html, "html.parser")
        tweet_cards = soup.find_all("div", class_="timeline-item")

        docs = []
        for card in tweet_cards[:max_items]:
            content_div = card.find("div", class_="tweet-content")
            if not content_div:
                continue

            text = content_div.get_text(strip=True)
            username_elem = card.find("a", class_="username")
            username = username_elem.get_text(strip=True) if username_elem else "Anonymous"

            link_elem = card.find("a", class_="tweet-link")
            link = link_elem["href"] if link_elem and link_elem.get("href") else ""

            docs.append(
                StandardDocument(
                    source_platform=self.PLATFORM_NAME,
                    source_url=link,
                    doc_type="post",
                    text=text,
                    author=username,
                    doc_id=f"nitter-{hash(text) & 0xFFFFFFFF:x}",
                )
            )

        return ScrapedContent(
            platform=self.PLATFORM_NAME,
            target=source_url,
            target_type="twitter_nitter",
            documents=docs,
            total_scraped=len(docs),
            source_metadata={"tweets_parsed": len(docs)},
        )

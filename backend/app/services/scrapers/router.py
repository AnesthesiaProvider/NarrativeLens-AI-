"""Universal scraper that routes any URL or target to the correct platform scraper."""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Type

from .base import BaseScraper, ScrapedContent

logger = logging.getLogger(__name__)


# Platform URL patterns (compiled once)
PLATFORM_PATTERNS: Dict[str, re.Pattern] = {
    "reddit":    re.compile(r"(?:https?://)?(?:www\.)?(?:old\.)?(?:new\.)?reddit\.com|redd\.it", re.IGNORECASE),
    "twitter":   re.compile(r"(?:https?://)?(?:www\.)?(?:twitter\.com|x\.com|nitter\.\w+)", re.IGNORECASE),
    "youtube":   re.compile(r"(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be|m\.youtube\.com)", re.IGNORECASE),
    "4chan":      re.compile(r"(?:https?://)?(?:boards\.)?4chan(?:nel)?\.org", re.IGNORECASE),
    "telegram":  re.compile(r"(?:https?://)?(?:t\.me|telegram\.me)", re.IGNORECASE),
    "instagram": re.compile(r"(?:https?://)?(?:www\.)?(?:instagram\.com|instagr\.am)", re.IGNORECASE),
    "tiktok":    re.compile(r"(?:https?://)?(?:www\.)?(?:tiktok\.com|vm\.tiktok\.com)", re.IGNORECASE),
    "facebook":  re.compile(r"(?:https?://)?(?:www\.)?(?:facebook\.com|fb\.com|fb\.watch)", re.IGNORECASE),
}


class UniversalScraper:
    """Routes any URL or target to the correct platform scraper."""
    
    def __init__(self):
        self._scrapers: Dict[str, BaseScraper] = {}
        self._register_scrapers()
    
    def _register_scrapers(self) -> None:
        """Register all available platform scrapers."""
        # Import scrapers lazily to avoid import errors if dependencies missing
        try:
            from .reddit_scraper import RedditScraper
            self._scrapers["reddit"] = RedditScraper()
            logger.info("Reddit scraper registered")
        except Exception as e:
            logger.warning(f"Reddit scraper not available: {e}")
        
        try:
            from .chan_scraper import ChanScraper
            self._scrapers["4chan"] = ChanScraper()
            logger.info("4chan scraper registered")
        except Exception as e:
            logger.warning(f"4chan scraper not available: {e}")
        
        try:
            from .twitter_scraper import TwitterScraper
            self._scrapers["twitter"] = TwitterScraper()
            logger.info("Twitter scraper registered")
        except Exception as e:
            logger.warning(f"Twitter scraper not available: {e}")
        
        try:
            from .web_scraper import WebScraper
            self._scrapers["web"] = WebScraper()
            logger.info("Web article scraper registered")
        except Exception as e:
            logger.warning(f"Web scraper not available: {e}")

        try:
            from .youtube_scraper import YouTubeScraper
            self._scrapers["youtube"] = YouTubeScraper()
            logger.info("YouTube scraper registered")
        except Exception as e:
            logger.warning(f"YouTube scraper not available: {e}")
    
    def detect_platform(self, target: str) -> str:
        """Detect which platform a target URL or shorthand belongs to."""
        t = target.strip()

        # Check registered scrapers in priority order
        for name, scraper in self._scrapers.items():
            if name != "web" and scraper.can_handle(t):
                return name

        # URL pattern matching fallback
        for platform, pattern in PLATFORM_PATTERNS.items():
            if pattern.search(t):
                return platform

        # Subreddit reference
        if t.startswith("r/") or t.startswith("/r/"):
            return "reddit"

        # 4chan shorthand like "/pol/" or common boards
        cleaned = t.strip("/")
        if cleaned.lower() in ("pol", "b", "news", "biz", "v", "int", "k", "tv", "g", "a", "his"):
            return "4chan"

        # Hashtag or Twitter handle
        if t.startswith("#") or t.startswith("@"):
            return "twitter"

        # Default to web
        return "web"
    
    def get_scraper(self, platform: str) -> Optional[BaseScraper]:
        """Get the scraper for a given platform."""
        return self._scrapers.get(platform)
    
    @property
    def available_platforms(self) -> List[str]:
        """List all registered/available platform scrapers."""
        return list(self._scrapers.keys())
    
    async def scrape(self, target: str, max_items: int = 50, platform: Optional[str] = None, **kwargs) -> ScrapedContent:
        """Scrape content from any URL or target.
        
        Args:
            target: URL, subreddit name, search query, etc.
            max_items: Maximum items to scrape.
            platform: Override auto-detection with explicit platform name.
            **kwargs: Platform-specific options.
            
        Returns:
            ScrapedContent with all scraped documents.
        """
        detected = platform or self.detect_platform(target)
        scraper = self.get_scraper(detected)
        
        if not scraper:
            # Fall back to web scraper
            scraper = self.get_scraper("web")
            if not scraper:
                return ScrapedContent(
                    platform=detected,
                    target=target,
                    target_type="unknown",
                    errors=[f"No scraper available for platform '{detected}'. Available: {self.available_platforms}"],
                )
        
        logger.info(f"Routing target '{target[:80]}' to {detected} scraper")
        return await scraper.scrape(target, max_items=max_items, **kwargs)


# Global singleton
universal_scraper = UniversalScraper()

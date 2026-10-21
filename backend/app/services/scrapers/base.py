"""Base classes and StandardDocument schema for the universal scraping pipeline."""

from __future__ import annotations

import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class StandardDocument:
    """Universal document format that every platform scraper outputs.
    
    The analysis pipeline receives the same shape regardless of source platform.
    """
    # Source identification
    source_platform: str         # "reddit", "twitter", "4chan", "telegram", "youtube", "web", etc.
    source_url: str              # Original URL of the content
    doc_type: str                # "post", "comment", "reply", "article", "message", "thread"
    
    # Content
    title: str = ""              # Post title, article headline, thread subject
    text: str = ""               # Main text body
    author: str = "Anonymous"    # Username / handle / display name
    author_id: str = ""          # Platform-specific user ID
    
    # Media
    image_urls: List[str] = field(default_factory=list)   # Attached image URLs
    image_bytes_list: List[bytes] = field(default_factory=list)  # Downloaded image data (for CLIP)
    video_urls: List[str] = field(default_factory=list)   # Video URLs
    
    # Engagement metrics
    score: int = 0               # Upvotes, likes, reactions
    reply_count: int = 0         # Number of replies
    view_count: int = 0          # Views if available
    
    # Timestamps
    published_at: Optional[datetime] = None  # When originally posted
    scraped_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Language
    language: str = "en"         # ISO 639-1 language code
    
    # Platform-specific metadata
    subreddit: str = ""          # Reddit subreddit name
    board: str = ""              # 4chan board name
    hashtags: List[str] = field(default_factory=list)
    mentions: List[str] = field(default_factory=list)
    extra_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Threading
    parent_id: Optional[str] = None   # Parent post/comment ID
    thread_id: Optional[str] = None   # Root thread/conversation ID
    doc_id: str = ""                  # Unique ID for this document
    
    # Deduplication hashes
    content_hash: str = ""       # SHA-256 of text content
    perceptual_hash: Optional[str] = None  # pHash of first image
    
    def __post_init__(self):
        """Compute content hash after initialization."""
        if self.text and not self.content_hash:
            self.content_hash = hashlib.sha256(self.text.encode("utf-8")).hexdigest()
        if not self.doc_id:
            self.doc_id = self.content_hash[:16] or hashlib.sha256(
                f"{self.source_platform}:{self.source_url}:{self.author}:{self.published_at}".encode()
            ).hexdigest()[:16]


@dataclass 
class ScrapedContent:
    """Container for a complete scrape result from any platform."""
    platform: str
    target: str                # Original target URL or query
    target_type: str           # "thread", "subreddit", "channel", "search", "article", etc.
    
    # Main content (the post/article/thread OP)
    main_document: Optional[StandardDocument] = None
    
    # All documents (comments, replies, posts)
    documents: List[StandardDocument] = field(default_factory=list)
    
    # Metadata about the scrape
    total_scraped: int = 0
    scrape_duration_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)
    scraped_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Source metadata (channel name, subreddit info, etc.)
    source_metadata: Dict[str, Any] = field(default_factory=dict)


class BaseScraper(ABC):
    """Abstract base class for all platform scrapers."""
    
    PLATFORM_NAME: str = "unknown"
    
    def __init__(self):
        self.logger = logging.getLogger(f"scraper.{self.PLATFORM_NAME}")
    
    @abstractmethod
    async def scrape(self, target: str, max_items: int = 50, **kwargs) -> ScrapedContent:
        """Scrape content from the platform.
        
        Args:
            target: URL, username, search query, or platform-specific identifier.
            max_items: Maximum number of items to scrape.
            **kwargs: Platform-specific options.
            
        Returns:
            ScrapedContent with all scraped documents.
        """
        ...
    
    @abstractmethod
    def can_handle(self, target: str) -> bool:
        """Check if this scraper can handle the given target URL or identifier."""
        ...
    
    def _make_document(self, **kwargs) -> StandardDocument:
        """Helper to create a StandardDocument with platform pre-filled."""
        return StandardDocument(source_platform=self.PLATFORM_NAME, **kwargs)

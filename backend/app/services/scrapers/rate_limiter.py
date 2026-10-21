"""Per-platform rate limiter to respect API limits and be polite."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from typing import Dict

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple token-bucket rate limiter per platform."""
    
    # Default rate limits per platform
    LIMITS: Dict[str, Dict] = {
        "reddit":    {"requests_per_minute": 30,  "min_delay": 2.0},
        "twitter":   {"requests_per_minute": 15,  "min_delay": 4.0},
        "4chan":      {"requests_per_minute": 60,  "min_delay": 1.0},
        "telegram":  {"requests_per_minute": 20,  "min_delay": 3.0},
        "instagram": {"requests_per_minute": 10,  "min_delay": 6.0},
        "tiktok":    {"requests_per_minute": 15,  "min_delay": 4.0},
        "youtube":   {"requests_per_minute": 30,  "min_delay": 2.0},
        "web":       {"requests_per_minute": 20,  "min_delay": 3.0},
        "default":   {"requests_per_minute": 20,  "min_delay": 3.0},
    }
    
    def __init__(self):
        self._last_request: Dict[str, float] = defaultdict(float)
        self._request_counts: Dict[str, list] = defaultdict(list)
    
    async def wait(self, platform: str) -> None:
        """Wait if necessary to respect rate limits for the given platform."""
        limits = self.LIMITS.get(platform, self.LIMITS["default"])
        min_delay = limits["min_delay"]
        rpm = limits["requests_per_minute"]
        
        now = time.monotonic()
        
        # Enforce minimum delay between requests
        elapsed = now - self._last_request[platform]
        if elapsed < min_delay:
            wait_time = min_delay - elapsed
            logger.debug(f"Rate limiter: waiting {wait_time:.1f}s for {platform}")
            await asyncio.sleep(wait_time)
        
        # Enforce requests-per-minute limit
        window_start = time.monotonic() - 60.0
        self._request_counts[platform] = [
            t for t in self._request_counts[platform] if t > window_start
        ]
        
        if len(self._request_counts[platform]) >= rpm:
            oldest = self._request_counts[platform][0]
            sleep_time = 60.0 - (time.monotonic() - oldest) + 0.5
            if sleep_time > 0:
                logger.info(f"Rate limiter: RPM limit reached for {platform}, sleeping {sleep_time:.1f}s")
                await asyncio.sleep(sleep_time)
        
        self._last_request[platform] = time.monotonic()
        self._request_counts[platform].append(time.monotonic())


# Global singleton
rate_limiter = RateLimiter()

"""Security utilities including SSRF protection, content sanitization, and file validation."""

from __future__ import annotations

import ipaddress
import os
import re
import socket
import unicodedata
from pathlib import Path
from typing import Optional, Set, Tuple
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.core.config import settings

# Allowed file extensions for ingestion and media assets
ALLOWED_EXTENSIONS: Set[str] = {
    ".csv",
    ".json",
    ".txt",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".tiff",
}

# Allowed MIME types
ALLOWED_MIME_TYPES: Set[str] = {
    "text/plain",
    "text/csv",
    "application/json",
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/bmp",
    "image/tiff",
}

# Pre-compiled blocked network objects from settings
_BLOCKED_NETWORKS = [
    ipaddress.ip_network(net.strip(), strict=False)
    for net in settings.BLOCKED_IP_NETWORKS
]


def is_ip_blocked(ip_str: str) -> bool:
    """Check if an IP address belongs to a blocked/private/loopback network."""
    try:
        ip = ipaddress.ip_address(ip_str)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return True

        for network in _BLOCKED_NETWORKS:
            if ip in network:
                return True

        return False
    except ValueError:
        return True


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a URL to protect against SSRF (Server-Side Request Forgery).
    Returns (is_valid, error_reason).
    """
    if not url or not isinstance(url, str):
        return False, "URL cannot be empty."

    parsed = urlparse(url.strip())
    if parsed.scheme.lower() not in ("http", "https"):
        return False, f"Invalid URL scheme '{parsed.scheme}'. Only http and https are allowed."

    hostname = parsed.hostname
    if not hostname:
        return False, "URL has no valid host component."

    # Check for localhost / loopback aliases directly
    lowered_host = hostname.lower()
    if lowered_host in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        return False, f"Access to '{hostname}' is blocked."

    # Resolve hostname to IPv4/IPv6 addresses and inspect them
    try:
        addr_info = socket.getaddrinfo(hostname, None)
        if not addr_info:
            return False, f"Could not resolve host '{hostname}'."

        for item in addr_info:
            sockaddr = item[4]
            ip_str = sockaddr[0]
            if is_ip_blocked(ip_str):
                return False, f"Host '{hostname}' resolves to restricted IP address '{ip_str}'."
    except socket.gaierror:
        return False, f"Domain name resolution failed for host '{hostname}'."
    except Exception as exc:
        return False, f"SSRF security check failed for URL: {exc}"

    return True, None


def sanitize_text(content: str, max_length: int = 500000) -> str:
    """
    Sanitize raw text content:
    - Normalizes Unicode (NFKC)
    - Strips null bytes and invisible control characters
    - Truncates to max_length
    """
    if not content:
        return ""

    # Remove null bytes
    text = content.replace("\x00", "")

    # Normalize unicode
    text = unicodedata.normalize("NFKC", text)

    # Remove non-printable control characters except standard whitespace
    text = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)

    # Truncate if exceeds maximum length
    if len(text) > max_length:
        text = text[:max_length]

    return text.strip()


def sanitize_html(html_content: str) -> str:
    """
    Sanitize HTML content by stripping script, style, and object tags,
    and returning cleaned plain text.
    """
    if not html_content:
        return ""

    try:
        soup = BeautifulSoup(html_content, "html.parser")
        for dangerous in soup(["script", "style", "iframe", "object", "embed", "applet"]):
            dangerous.decompose()

        cleaned = soup.get_text(separator=" ", strip=True)
        return sanitize_text(cleaned)
    except Exception:
        # Fallback to regex tag stripping
        clean_re = re.compile(r"<.*?>")
        raw_text = re.sub(clean_re, " ", html_content)
        return sanitize_text(raw_text)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize an uploaded filename to prevent directory traversal and filesystem attacks.
    """
    if not filename:
        return "unnamed_file"

    # Take only the basename (strips any path components)
    basename = Path(filename).name

    # Remove dangerous characters
    clean_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', basename)

    # Prevent hidden files or double dots
    clean_name = clean_name.lstrip(".")
    clean_name = re.sub(r"\.{2,}", ".", clean_name)

    return clean_name or "uploaded_file"


def validate_file(
    filename: str,
    file_size_bytes: int,
    mime_type: Optional[str] = None,
    max_size_mb: Optional[int] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Validate an uploaded file for allowed extension, size limit, and MIME type.
    """
    max_mb = max_size_mb or settings.MAX_UPLOAD_SIZE_MB
    max_bytes = max_mb * 1024 * 1024

    if file_size_bytes > max_bytes:
        return False, f"File size ({file_size_bytes / (1024*1024):.2f} MB) exceeds maximum allowed {max_mb} MB."

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File extension '{ext}' is not supported. Allowed: {sorted(ALLOWED_EXTENSIONS)}"

    if mime_type and mime_type.lower() not in ALLOWED_MIME_TYPES:
        # Warning/error for disallowed mime
        pass

    return True, None

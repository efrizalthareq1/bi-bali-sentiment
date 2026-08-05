"""Resolve publisher URLs from Google News RSS redirect links."""

from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import parse_qs, unquote, urlparse

logger = logging.getLogger(__name__)

_GOOGLE_HOSTS = ("news.google.com", "news.google.co.id")


def is_google_news_url(url: Optional[str]) -> bool:
    if not url:
        return False
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    return any(h in host for h in _GOOGLE_HOSTS)


def is_demo_or_placeholder_url(url: Optional[str]) -> bool:
    if not url:
        return True
    lowered = url.lower()
    return any(
        marker in lowered
        for marker in (
            "example.com",
            "/demo-",
            "ig-demo-",
            "tt-demo-",
            "dummy-",
        )
    )


def _fast_google_news_url(url: str) -> str:
    """Cheap, no-network conversion to an openable Google News page."""
    if "/rss/articles/" in url:
        return url.replace("/rss/articles/", "/articles/")
    return url


def _decode_with_gnewsdecoder(url: str) -> Optional[str]:
    try:
        from googlenewsdecoder import new_decoderv1

        result = new_decoderv1(url)
        if isinstance(result, dict) and result.get("status") and result.get("decoded_url"):
            return result["decoded_url"]
    except Exception:
        pass

    try:
        from googlenewsdecoder import gnewsdecoder

        result = gnewsdecoder(url)
        if isinstance(result, dict) and result.get("status") and result.get("decoded_url"):
            return result["decoded_url"]
        if isinstance(result, str) and result.startswith("http"):
            return result
    except Exception as exc:
        logger.debug("googlenewsdecoder failed: %s", exc)
    return None


def resolve_article_url(url: Optional[str], *, fast: bool = False) -> Optional[str]:
    """
    Return a clickable publisher URL when possible.

    fast=True skips googlenewsdecoder (network-heavy) so RSS sync stays quick.
    Use the /posts/resolve-urls endpoint later to decode publisher URLs in bulk.
    """
    if not url:
        return None
    url = url.strip()
    if not url:
        return None

    # Older Google News format: ...?url=https%3A%2F%2Fpublisher...
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "url" in qs and qs["url"]:
        candidate = unquote(qs["url"][0])
        if candidate.startswith("http") and "news.google.com" not in candidate:
            return candidate

    if not is_google_news_url(url):
        return url

    if fast:
        return _fast_google_news_url(url)

    decoded = _decode_with_gnewsdecoder(url)
    if decoded and not is_google_news_url(decoded):
        return decoded

    return _fast_google_news_url(url)

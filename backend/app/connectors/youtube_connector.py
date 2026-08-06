"""YouTube connector — video publik yang membahas BI (bukan hanya channel resmi)."""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import List, Optional, Set
from urllib.parse import quote_plus, parse_qs, urlparse

import feedparser

from app.connectors.base import BaseConnector, RawPost
from app.services.url_resolve import resolve_article_url

logger = logging.getLogger(__name__)

# Channel / author resmi BI — dikecualikan agar fokus konten publik/netizen
OFFICIAL_YT_AUTHORS: Set[str] = {
    "bank indonesia channel",
    "bank indonesia",
    "bankindonesia",
    "bi channel",
}

TOPIC_QUERIES = [
    '"Bank Indonesia" (inflasi OR "BI-Rate" OR QRIS OR GPIPS) site:youtube.com',
    '"QRIS Run" site:youtube.com',
    '"QRIS Summer Run" site:youtube.com',
    'qrissummerrun site:youtube.com',
    '"BI-Rate" Bank Indonesia site:youtube.com',
    'GPIPS OR GPIB "Bank Indonesia" site:youtube.com',
    '"Bank Indonesia Bali" OR "BI Bali" site:youtube.com',
    'inflasi Indonesia "Bank Indonesia" site:youtube.com',
]


def _parse_entry_date(entry) -> datetime:
    for attr in ("published", "updated"):
        raw = getattr(entry, attr, None)
        if raw:
            try:
                dt = parsedate_to_datetime(raw)
                if dt.tzinfo:
                    dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                return dt
            except (TypeError, ValueError, IndexError):
                pass
    return datetime.utcnow()


def _video_id_from_blob(blob: str) -> Optional[str]:
    m = re.search(
        r"(?:https?://)?(?:www\.)?youtu(?:\.be/|be\.com/(?:watch\?v=|shorts/|live/))([\w-]{6,})",
        blob,
        re.I,
    )
    return m.group(1) if m else None


def _is_official_author(author: Optional[str]) -> bool:
    if not author:
        return False
    return author.strip().lower() in OFFICIAL_YT_AUTHORS


class YouTubeConnector(BaseConnector):
    id = "youtube"
    name = "YouTube"
    description = (
        "Video YouTube publik yang membahas Bank Indonesia / isu kebijakan "
        "(bukan hanya channel resmi BI)."
    )
    requires_api_key = False

    def is_configured(self) -> bool:
        return True

    def fetch_posts(self, keywords: List[str], limit: int = 50) -> List[RawPost]:
        posts = self._fetch_google_youtube_search(keywords, limit=limit)
        clean: List[RawPost] = []
        seen: set[str] = set()
        for p in posts:
            if _is_official_author(p.author):
                continue
            if p.source_post_id in seen:
                continue
            seen.add(p.source_post_id)
            clean.append(p)
        return clean[:limit]

    def _fetch_google_youtube_search(self, keywords: List[str], limit: int) -> List[RawPost]:
        keys = [k for k in keywords if k and not k.startswith("#")][:8] or [
            "Bank Indonesia",
            "Bank Indonesia Bali",
            "GPIPS",
            "inflasi Bank Indonesia",
            "QRIS Run",
            "QRIS Summer Run",
            "qrissummerrun",
            "QRIS Bali",
            "BI-Rate",
        ]
        for extra in (
            "GPIPS Bank Indonesia",
            "inflasi Indonesia BI",
            "QRIS Bank Indonesia",
            "QRIS Run",
            "BI-Rate Bank Indonesia",
        ):
            if extra not in keys:
                keys.append(extra)
        keys = keys[:10]

        results: List[RawPost] = []
        seen: set[str] = set()

        queries = [f'"{kw}" site:youtube.com' for kw in keys]
        queries.extend(TOPIC_QUERIES)

        for query in queries:
            if len(results) >= limit:
                break
            url = (
                "https://news.google.com/rss/search?"
                f"q={quote_plus(query)}&hl=id&gl=ID&ceid=ID:id"
            )
            try:
                feed = feedparser.parse(url)
            except Exception as exc:
                logger.warning("YouTube search RSS failed: %s", exc)
                continue

            for entry in feed.entries:
                if len(results) >= limit:
                    break
                title = getattr(entry, "title", "") or ""
                summary = getattr(entry, "summary", "") or ""
                link = getattr(entry, "link", "") or ""
                blob = f"{title}\n{summary}\n{link}"

                resolved = None
                vid = _video_id_from_blob(blob)
                if vid:
                    resolved = f"https://www.youtube.com/watch?v={vid}"
                elif len(results) < 10:
                    try:
                        candidate = resolve_article_url(link) or ""
                    except Exception:
                        candidate = ""
                    if "youtube.com" in candidate or "youtu.be" in candidate:
                        parsed = urlparse(candidate)
                        if "youtu.be" in parsed.netloc:
                            vid = parsed.path.strip("/")
                            resolved = f"https://www.youtube.com/watch?v={vid}"
                        else:
                            qs = parse_qs(parsed.query)
                            if "v" in qs:
                                vid = qs["v"][0]
                                resolved = f"https://www.youtube.com/watch?v={vid}"
                            else:
                                m = re.search(r"/shorts/([\w-]{6,})", candidate)
                                if m:
                                    vid = m.group(1)
                                    resolved = f"https://www.youtube.com/watch?v={vid}"

                if not resolved:
                    continue

                source_id = vid or hashlib.sha256(resolved.encode()).hexdigest()[:16]
                if source_id in seen:
                    continue
                seen.add(source_id)

                author = None
                src = getattr(entry, "source", None)
                if isinstance(src, dict):
                    author = src.get("title")
                author = author or "YouTube"
                if _is_official_author(author):
                    continue

                matched = next(
                    (k for k in keys if k.lower() in title.lower()),
                    keys[0],
                )
                results.append(
                    RawPost(
                        source="youtube",
                        source_post_id=source_id,
                        author=author,
                        text_raw=title[:5000],
                        url=resolved,
                        posted_at=_parse_entry_date(entry),
                        keyword_matched=matched,
                    )
                )
        return results

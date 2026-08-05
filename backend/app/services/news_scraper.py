"""News RSS / Google News scraper for Indonesian outlets (legal free sources)."""

from __future__ import annotations

import hashlib
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable, List, Optional
from urllib.parse import quote_plus

import feedparser
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.constants import DEFAULT_KEYWORDS
from app.models import Keyword, Post
from app.services.url_resolve import resolve_article_url

logger = logging.getLogger(__name__)

# Cap sync size so the UI does not hang waiting for dozens of keyword feeds.
DEFAULT_NEWS_KEYWORD_LIMIT = 18
DEFAULT_PER_KEYWORD_LIMIT = 15


def _google_news_rss(query: str, lang: str = "id", country: str = "ID") -> str:
    return (
        f"https://news.google.com/rss/search?"
        f"q={quote_plus(query)}&hl={lang}&gl={country}&ceid={country}:{lang}"
    )


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


def _make_source_id(url: str, title: str) -> str:
    raw = f"{url}|{title}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:32]


def fetch_news_for_keyword(keyword: str, limit: int = 20) -> List[dict]:
    """Fetch Google News RSS items for a keyword. Returns dicts ready for Post."""
    url = _google_news_rss(keyword)
    feed = feedparser.parse(url)
    items: List[dict] = []
    for entry in feed.entries[:limit]:
        title = getattr(entry, "title", "") or ""
        summary = getattr(entry, "summary", "") or ""
        link = getattr(entry, "link", "") or ""
        author = getattr(entry, "source", {})
        if isinstance(author, dict):
            author_name = author.get("title")
        else:
            author_name = getattr(entry, "author", None)

        text = title
        if summary and summary not in title:
            clean = re.sub(r"<[^>]+>", " ", summary)
            clean = clean.replace("&nbsp;", " ").replace("&amp;", "&")
            clean = re.sub(r"\s+", " ", clean).strip()
            if clean:
                text = f"{title}. {clean}"

        if not text.strip():
            continue

        # fast=True: skip googlenewsdecoder (was making sync take minutes)
        resolved = resolve_article_url(link, fast=True) or link

        items.append(
            {
                "source": "news",
                "source_post_id": _make_source_id(link, title),
                "author": author_name,
                "text_raw": text[:5000],
                "url": resolved,
                "posted_at": _parse_entry_date(entry),
                "keyword_matched": keyword,
            }
        )
    return items


def get_active_keywords(db: Session) -> List[str]:
    """Text keywords for news/search — excludes Instagram hashtag catalog."""
    rows = (
        db.query(Keyword)
        .filter(Keyword.active.is_(True))
        .filter(~Keyword.category.like("ig_%"))
        .filter(~Keyword.keyword.like("#%"))
        .all()
    )
    if rows:
        return [r.keyword for r in rows]
    return [k for k, _ in DEFAULT_KEYWORDS]


def get_active_instagram_hashtags(db: Session, limit: Optional[int] = None) -> List[str]:
    """Active Instagram hashtags from DB, priority-ordered when possible."""
    from app.instagram_hashtags import INSTAGRAM_PRIORITY_HASHTAGS, format_hashtag

    rows = (
        db.query(Keyword)
        .filter(Keyword.active.is_(True))
        .filter(
            (Keyword.category.like("ig_%")) | (Keyword.keyword.like("#%"))
        )
        .all()
    )
    if not rows:
        tags = [format_hashtag(t) for t in INSTAGRAM_PRIORITY_HASHTAGS]
        return tags[:limit] if limit else tags

    priority_index = {
        format_hashtag(t).lower(): i for i, t in enumerate(INSTAGRAM_PRIORITY_HASHTAGS)
    }
    tags = [r.keyword if r.keyword.startswith("#") else format_hashtag(r.keyword) for r in rows]
    tags = sorted(
        tags,
        key=lambda t: priority_index.get(t.lower(), 10_000),
    )
    if limit:
        return tags[:limit]
    return tags


def _news_keyword_priority(keyword: str) -> int:
    """Prefer core BI / Bali / policy terms during capped syncs."""
    preferred = [
        "bank indonesia bali",
        "bank indonesia",
        "bi bali",
        "kpwbi bali",
        "qris run",
        "gpips",
        "inflasi",
        "qris",
        "bi-rate",
        "suku bunga",
        "umkm",
        "rupiah",
    ]
    lowered = keyword.lower()
    for i, needle in enumerate(preferred):
        if needle in lowered:
            return i
    return 100


def sync_news(
    db: Session,
    keywords: Optional[Iterable[str]] = None,
    per_keyword_limit: int = DEFAULT_PER_KEYWORD_LIMIT,
    max_keywords: int = DEFAULT_NEWS_KEYWORD_LIMIT,
) -> tuple[int, int]:
    """Fetch news for keywords and insert new posts. Returns (inserted, skipped)."""
    keys = list(keywords) if keywords else get_active_keywords(db)
    keys = sorted(keys, key=_news_keyword_priority)
    if max_keywords and len(keys) > max_keywords:
        keys = keys[:max_keywords]

    inserted = 0
    skipped = 0
    collected: List[dict] = []

    # Parallel RSS fetches (I/O bound) — much faster than sequential
    workers = min(6, max(1, len(keys)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(fetch_news_for_keyword, kw, per_keyword_limit): kw for kw in keys
        }
        for fut in as_completed(futures):
            kw = futures[fut]
            try:
                collected.extend(fut.result())
            except Exception as exc:
                logger.warning("News fetch failed for '%s': %s", kw, exc)

    # Deduplicate within this batch by source_post_id
    seen_ids: set[str] = set()
    unique_items: List[dict] = []
    for item in collected:
        sid = item["source_post_id"]
        if sid in seen_ids:
            skipped += 1
            continue
        seen_ids.add(sid)
        unique_items.append(item)

    for item in unique_items:
        post = Post(**item)
        db.add(post)
        try:
            db.commit()
            inserted += 1
        except IntegrityError:
            db.rollback()
            skipped += 1

    return inserted, skipped

"""Connector registry and sync helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.connectors.base import BaseConnector, ConnectorInfo, RawPost
from app.connectors.instagram_connector import InstagramConnector
from app.connectors.news_connector import NewsConnector
from app.connectors.outlook_connector import OutlookConnector
from app.connectors.threads_connector import ThreadsConnector
from app.connectors.tiktok_connector import TikTokConnector
from app.connectors.x_connector import XConnector
from app.connectors.youtube_connector import YouTubeConnector
from app.models import Post, SentimentScore
from app.services.news_scraper import (
    _news_keyword_priority,
    get_active_instagram_hashtags,
    get_active_keywords,
)

_LAST_SYNC: Dict[str, datetime] = {}


def get_connectors() -> List[BaseConnector]:
    return [
        NewsConnector(),
        OutlookConnector(),
        XConnector(),
        YouTubeConnector(),
        ThreadsConnector(),
        InstagramConnector(),
        TikTokConnector(),
    ]


def get_connector(connector_id: str) -> Optional[BaseConnector]:
    for c in get_connectors():
        if c.id == connector_id:
            return c
    return None


def list_connector_status(db: Session) -> List[ConnectorInfo]:
    infos: List[ConnectorInfo] = []
    for connector in get_connectors():
        count = db.query(Post).filter(Post.source == connector.id).count()
        infos.append(
            connector.get_info(post_count=count, last_sync=_LAST_SYNC.get(connector.id))
        )
    manual_count = db.query(Post).filter(Post.source == "manual").count()
    infos.append(
        ConnectorInfo(
            id="manual",
            name="Upload Manual (CSV/Excel)",
            description="Impor data dari file CSV atau Excel melalui endpoint /ingest/upload.",
            requires_api_key=False,
            configured=True,
            status="ready",
            post_count=manual_count,
            last_sync=_LAST_SYNC.get("manual"),
        )
    )
    dummy_count = db.query(Post).filter(
        or_(
            Post.source_post_id.like("dummy-%"),
            Post.source_post_id.like("%-demo-%"),
            Post.url.ilike("%example.com%"),
            Post.url.ilike("%/demo%"),
        )
    ).count()
    infos.append(
        ConnectorInfo(
            id="dummy",
            name="Data Sintetis",
            description="Generator data dummy untuk pengujian dashboard.",
            requires_api_key=False,
            configured=True,
            status="ready",
            post_count=dummy_count,
            last_sync=_LAST_SYNC.get("dummy"),
        )
    )
    return infos


def persist_raw_posts(db: Session, posts: List[RawPost]) -> tuple[int, int]:
    inserted = 0
    skipped = 0
    for raw in posts:
        db.add(
            Post(
                source=raw.source,
                source_post_id=raw.source_post_id,
                author=raw.author,
                text_raw=raw.text_raw,
                url=raw.url,
                posted_at=raw.posted_at,
                keyword_matched=raw.keyword_matched,
            )
        )
        try:
            db.commit()
            inserted += 1
        except IntegrityError:
            db.rollback()
            skipped += 1
    return inserted, skipped


def purge_demo_posts(db: Session, sources: Optional[List[str]] = None) -> int:
    """Remove placeholder/demo posts and official BI profile stubs."""
    query = db.query(Post).filter(
        or_(
            Post.source_post_id.like("%-demo-%"),
            Post.source_post_id.like("demo-%"),
            Post.source_post_id.like("dummy-%"),
            Post.source_post_id.like("x-demo-%"),
            Post.source_post_id.like("ig-demo-%"),
            Post.source_post_id.like("tt-demo-%"),
            Post.source_post_id.like("outlook-demo-%"),
            Post.source_post_id.like("profile-%"),
            Post.url.ilike("%example.com%"),
            Post.url.ilike("%watch?v=demo%"),
            Post.url.ilike("%/post/demo%"),
            Post.url.ilike("%threads.net/%/post/demo%"),
            Post.url.ilike("%outlook.office.com%/demo/%"),
            # Official account timeline stubs / posts (we want netizen discussion)
            Post.author.ilike("bank_indonesia"),
            Post.author.ilike("BI_ProvinsiAceh"),
            Post.author.ilike("bankindonesia"),
            Post.author.ilike("Bank Indonesia Channel"),
            Post.keyword_matched.ilike("@bank_indonesia"),
            Post.keyword_matched.ilike("@bankindonesia"),
            Post.keyword_matched.ilike("@BI_ProvinsiAceh"),
        )
    )
    if sources:
        query = query.filter(Post.source.in_(sources))
    rows = query.all()
    deleted = 0
    for post in rows:
        db.query(SentimentScore).filter(SentimentScore.post_id == post.id).delete()
        db.delete(post)
        deleted += 1
    db.commit()
    return deleted


def sync_connector(db: Session, connector_id: str, limit: int = 50) -> tuple[int, int]:
    connector = get_connector(connector_id)
    if not connector:
        raise ValueError(f"Connector tidak ditemukan: {connector_id}")
    if connector.requires_api_key and not connector.is_configured():
        raise ValueError(
            f"Connector {connector_id} belum dikonfigurasi. "
            "Isi INSTAGRAM_ACCESS_TOKEN dan INSTAGRAM_BUSINESS_ACCOUNT_ID di backend/.env "
            "untuk pencarian hashtag Graph API, atau gunakan /ingest/instagram-demo."
            if connector_id == "instagram"
            else (
                "Isi TIKTOK_CLIENT_KEY dan TIKTOK_CLIENT_SECRET, atau gunakan /ingest/tiktok-demo."
                if connector_id == "tiktok"
                else (
                    "Isi OUTLOOK_TENANT_ID, OUTLOOK_CLIENT_ID, OUTLOOK_CLIENT_SECRET, "
                    "OUTLOOK_MAILBOX (atau OUTLOOK_ACCESS_TOKEN), atau gunakan /ingest/outlook-demo."
                    if connector_id == "outlook"
                    else f"Connector {connector_id} belum dikonfigurasi (API key)."
                )
            )
        )

    if connector_id in {"youtube", "threads", "x", "instagram"}:
        purge_demo_posts(db, sources=[connector_id])

    if connector_id == "instagram":
        from app.config import get_settings

        # Prefer text keywords for public discussion; fall back to hashtag catalog
        text_kw = sorted(get_active_keywords(db), key=_news_keyword_priority)
        ig_tags = get_active_instagram_hashtags(
            db, limit=get_settings().instagram_hashtag_sync_limit
        )
        keywords = text_kw[:10] + ig_tags[:8]
        for extra in ("Bank Indonesia Aceh", "BI Aceh", "QRIS Aceh", "KPwBI Aceh"):
            if extra not in keywords:
                keywords = [extra, *keywords]
    elif connector_id == "tiktok":
        text_kw = sorted(get_active_keywords(db), key=_news_keyword_priority)[:8]
        ig_tags = get_active_instagram_hashtags(db, limit=8)
        keywords = text_kw + ig_tags
    else:
        keywords = sorted(get_active_keywords(db), key=_news_keyword_priority)
        if connector_id in {"news", "x", "youtube", "threads", "outlook"}:
            for extra in (
                "Bank Indonesia Aceh",
                "BI Aceh",
                "KPwBI Aceh",
                "QRIS Aceh",
                "inflasi Aceh",
            ):
                if extra not in keywords:
                    keywords = [extra, *keywords]

    raw_posts = connector.fetch_posts(keywords, limit=limit)
    inserted, skipped = persist_raw_posts(db, raw_posts)
    _LAST_SYNC[connector_id] = datetime.utcnow()
    return inserted, skipped

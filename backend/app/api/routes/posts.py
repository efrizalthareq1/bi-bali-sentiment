"""API routes for posts listing and detail."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Post, SentimentScore
from app.schemas import IngestResult, PostListResponse, PostOut
from app.services.url_resolve import (
    is_demo_or_placeholder_url,
    is_google_news_url,
    resolve_article_url,
)

router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("", response_model=PostListResponse)
def list_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    source: Optional[str] = None,
    sentiment: Optional[str] = None,
    keyword: Optional[str] = None,
    topic: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Post).options(joinedload(Post.sentiment))

    if source:
        query = query.filter(Post.source == source)
    if date_from:
        query = query.filter(Post.posted_at >= date_from)
    if date_to:
        query = query.filter(Post.posted_at <= date_to)
    if keyword:
        query = query.filter(Post.keyword_matched.ilike(f"%{keyword}%"))
    if q:
        query = query.filter(Post.text_raw.ilike(f"%{q}%"))
    if sentiment or topic:
        query = query.join(SentimentScore, isouter=False)
        if sentiment:
            query = query.filter(SentimentScore.sentiment == sentiment)
        if topic:
            query = query.filter(SentimentScore.topic_tag == topic)

    total = query.count()
    items = (
        query.order_by(Post.posted_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PostListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[PostOut.model_validate(p) for p in items],
    )


@router.post("/resolve-urls", response_model=IngestResult)
def resolve_stored_urls(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Backfill: convert Google News redirect URLs already in DB into publisher URLs."""
    import time

    rows = (
        db.query(Post)
        .filter(Post.url.isnot(None))
        .filter(Post.url.ilike("%news.google.com%"))
        .order_by(Post.posted_at.desc())
        .limit(limit)
        .all()
    )
    updated = 0
    skipped = 0
    for post in rows:
        resolved = resolve_article_url(post.url)
        if resolved and resolved != post.url and not is_google_news_url(resolved):
            post.url = resolved
            updated += 1
        else:
            skipped += 1
        time.sleep(0.15)
    db.commit()
    return IngestResult(
        inserted=updated,
        skipped=skipped,
        message=f"URL diperbaiki: {updated} berhasil, {skipped} dilewati.",
    )


@router.get("/{post_id}/open")
def open_post_source(post_id: int, db: Session = Depends(get_db)):
    """Redirect to a working publisher/source URL (resolves Google News links)."""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post tidak ditemukan")
    if not post.url:
        raise HTTPException(status_code=404, detail="Post ini tidak punya URL sumber")
    if is_demo_or_placeholder_url(post.url):
        raise HTTPException(
            status_code=400,
            detail="Ini data demo/sintetis — tidak ada tautan sumber asli yang bisa dibuka.",
        )

    resolved = resolve_article_url(post.url) or post.url
    if resolved != post.url and not is_google_news_url(resolved):
        post.url = resolved
        db.commit()

    return RedirectResponse(url=resolved, status_code=302)


@router.get("/{post_id}", response_model=PostOut)
def get_post(post_id: int, db: Session = Depends(get_db)):
    post = (
        db.query(Post)
        .options(joinedload(Post.sentiment))
        .filter(Post.id == post_id)
        .first()
    )
    if not post:
        raise HTTPException(status_code=404, detail="Post tidak ditemukan")
    return PostOut.model_validate(post)

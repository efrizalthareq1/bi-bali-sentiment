"""Background job: analyze posts that do not yet have sentiment scores."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Post, SentimentScore
from app.services.sentiment import analyze_text

logger = logging.getLogger(__name__)


def analyze_pending_posts(db: Session, batch_size: int = 50) -> int:
    """Analyze unanalyzed posts. Returns number of posts processed."""
    pending = (
        db.query(Post)
        .outerjoin(SentimentScore)
        .filter(SentimentScore.id.is_(None))
        .order_by(Post.posted_at.desc())
        .limit(batch_size)
        .all()
    )
    processed = 0
    for post in pending:
        try:
            result = analyze_text(post.text_raw, db=db, use_cache=True)
            db.add(
                SentimentScore(
                    post_id=post.id,
                    sentiment=result.sentiment,
                    confidence=result.confidence,
                    topic_tag=result.topic_tag,
                    reasoning=result.reasoning,
                    model_used=result.model_used or "unknown",
                )
            )
            db.commit()
            processed += 1
        except Exception as exc:
            db.rollback()
            logger.warning("Failed to analyze post %s: %s", post.id, exc)
    return processed


def run_analyze_job() -> int:
    db = SessionLocal()
    try:
        return analyze_pending_posts(db)
    finally:
        db.close()

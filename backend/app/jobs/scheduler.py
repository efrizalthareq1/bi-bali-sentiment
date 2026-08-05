"""APScheduler setup for periodic news sync and sentiment analysis."""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import get_settings
from app.database import SessionLocal
from app.jobs.analyzer import analyze_pending_posts
from app.services.news_scraper import sync_news

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def _job_sync_news() -> None:
    db = SessionLocal()
    try:
        inserted, skipped = sync_news(db)
        logger.info("News sync: inserted=%s skipped=%s", inserted, skipped)
    except Exception as exc:
        logger.exception("News sync failed: %s", exc)
    finally:
        db.close()


def _job_analyze() -> None:
    db = SessionLocal()
    try:
        n = analyze_pending_posts(db)
        if n:
            logger.info("Analyzed %s pending posts", n)
    except Exception as exc:
        logger.exception("Analyze job failed: %s", exc)
    finally:
        db.close()


def start_scheduler() -> None:
    settings = get_settings()
    if not settings.enable_scheduler:
        logger.info("Scheduler disabled via ENABLE_SCHEDULER")
        return
    if scheduler.running:
        return

    scheduler.add_job(
        _job_sync_news,
        "interval",
        minutes=settings.news_sync_interval_minutes,
        id="sync_news",
        replace_existing=True,
    )
    scheduler.add_job(
        _job_analyze,
        "interval",
        minutes=settings.analyze_interval_minutes,
        id="analyze_pending",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler started (news=%smin, analyze=%smin)",
        settings.news_sync_interval_minutes,
        settings.analyze_interval_minutes,
    )


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)

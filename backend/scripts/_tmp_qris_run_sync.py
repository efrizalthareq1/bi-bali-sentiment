"""One-off: sync QRIS Run news + social, analyze pending, report counts."""
from __future__ import annotations

import os

# Prefer SSH tunnel URL when running locally against Railway Postgres.
_tunnel = os.environ.get("TUNNEL_DATABASE_URL")
if _tunnel:
    os.environ["DATABASE_URL"] = _tunnel

from sqlalchemy import or_

from app.connectors import persist_raw_posts
from app.connectors.instagram_connector import InstagramConnector
from app.connectors.threads_connector import ThreadsConnector
from app.connectors.x_connector import XConnector
from app.connectors.youtube_connector import YouTubeConnector
from app.database import SessionLocal
from app.jobs.analyzer import analyze_pending_posts
from app.models import Post
from app.services.news_scraper import sync_news

NEWS_KEYWORDS = [
    "QRIS Run",
    "Bandung QRIS Run",
    "QRIS Bali Summer Run",
    "QRIS Torang Color Run",
    "Nusantara QRIS Run",
    "QRIS Run 2026",
]

X_KEYWORDS = ["QRIS Run", "Bandung QRIS Run", "QRIS Run 2026", "QRIS Bali"]
YT_IG_TH_KEYWORDS = [
    "QRIS Run",
    "Bandung QRIS Run",
    "QRIS Run 2026",
    "QRIS Bali",
    "QRIS Bali Summer Run",
]


def analyze_all_pending(db, rounds: int = 40, batch_size: int = 50) -> int:
    total = 0
    for _ in range(rounds):
        n = analyze_pending_posts(db, batch_size=batch_size)
        total += n
        if n == 0:
            break
    return total


def main() -> None:
    db = SessionLocal()
    try:
        print("=== 1. NEWS sync ===")
        news_ins, news_skip = sync_news(
            db,
            keywords=NEWS_KEYWORDS,
            per_keyword_limit=20,
            max_keywords=10,
        )
        print(f"news inserted={news_ins} skipped={news_skip}")
        news_analyzed = analyze_all_pending(db)
        print(f"news analyze_pending={news_analyzed}")

        print("=== 2. X fetch ===")
        x_posts = XConnector().fetch_posts(keywords=X_KEYWORDS, limit=80)
        x_ins, x_skip = persist_raw_posts(db, x_posts)
        print(f"x fetched={len(x_posts)} inserted={x_ins} skipped={x_skip}")
        x_analyzed = analyze_all_pending(db)
        print(f"x analyze_pending={x_analyzed}")

        print("=== 3. YouTube / Instagram / Threads ===")
        yt_posts = YouTubeConnector().fetch_posts(keywords=YT_IG_TH_KEYWORDS, limit=40)
        yt_ins, yt_skip = persist_raw_posts(db, yt_posts)
        print(f"youtube fetched={len(yt_posts)} inserted={yt_ins} skipped={yt_skip}")

        ig_posts = InstagramConnector().fetch_posts(keywords=YT_IG_TH_KEYWORDS, limit=40)
        ig_ins, ig_skip = persist_raw_posts(db, ig_posts)
        print(f"instagram fetched={len(ig_posts)} inserted={ig_ins} skipped={ig_skip}")

        th_posts = ThreadsConnector().fetch_posts(keywords=YT_IG_TH_KEYWORDS, limit=40)
        th_ins, th_skip = persist_raw_posts(db, th_posts)
        print(f"threads fetched={len(th_posts)} inserted={th_ins} skipped={th_skip}")

        social_analyzed = analyze_all_pending(db)
        print(f"yt/ig/th analyze_pending={social_analyzed}")

        print("=== INSERT SUMMARY ===")
        print(
            f"inserted: news={news_ins} x={x_ins} youtube={yt_ins} "
            f"instagram={ig_ins} threads={th_ins} "
            f"TOTAL={news_ins + x_ins + yt_ins + ig_ins + th_ins}"
        )

        q = db.query(Post).filter(
            or_(
                Post.text_raw.ilike("%QRIS Run%"),
                Post.keyword_matched.ilike("%QRIS Run%"),
            )
        )
        count = q.count()
        print(f"=== QRIS Run match count={count} ===")
        samples = q.order_by(Post.posted_at.desc()).limit(8).all()
        for i, p in enumerate(samples, 1):
            text = (p.text_raw or "")[:120].replace("\n", " ")
            print(f"{i}. source={p.source} author={p.author!r}")
            print(f"   text={text!r}")
            print(f"   url={p.url}")
    finally:
        db.close()


if __name__ == "__main__":
    main()

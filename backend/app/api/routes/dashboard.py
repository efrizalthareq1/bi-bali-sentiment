"""Dashboard aggregation endpoints."""

from collections import Counter
from datetime import datetime
from typing import Optional
import re

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from app.constants import STOPWORDS_ID
from app.database import get_db
from app.models import Post, SentimentScore
from app.schemas import (
    DashboardOverview,
    PlatformStat,
    SNAGraph,
    SummaryStats,
    TopicStat,
    TrendPoint,
    WordFreq,
)
from app.services.sna import build_sna_graph

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _text_search_filter(q: Optional[str]):
    if not q:
        return None
    parts = [p.strip() for p in re.split(r"\s+OR\s+|\|", q, flags=re.I) if p.strip()]
    if not parts:
        return None
    clauses = []
    for part in parts:
        like = f"%{part}%"
        clauses.append(Post.text_raw.ilike(like))
        clauses.append(Post.keyword_matched.ilike(like))
    return or_(*clauses)


def _base_filters(
    query,
    source: Optional[str],
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    keyword: Optional[str],
    q: Optional[str] = None,
):
    if source:
        query = query.filter(Post.source == source)
    if date_from:
        query = query.filter(Post.posted_at >= date_from)
    if date_to:
        query = query.filter(Post.posted_at <= date_to)
    if keyword:
        query = query.filter(Post.keyword_matched.ilike(f"%{keyword}%"))
    text_filter = _text_search_filter(q)
    if text_filter is not None:
        query = query.filter(text_filter)
    return query


@router.get("/overview", response_model=DashboardOverview)
def dashboard_overview(
    source: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    keyword: Optional[str] = None,
    sentiment: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
):
    posts_q = _base_filters(db.query(Post), source, date_from, date_to, keyword, q)
    if sentiment:
        posts_q = posts_q.join(SentimentScore).filter(SentimentScore.sentiment == sentiment)

    total = posts_q.count()

    # Sentiment counts
    sent_q = (
        db.query(SentimentScore.sentiment, func.count(SentimentScore.id))
        .join(Post)
    )
    sent_q = _base_filters(sent_q, source, date_from, date_to, keyword, q)
    if sentiment:
        sent_q = sent_q.filter(SentimentScore.sentiment == sentiment)
    sent_rows = dict(sent_q.group_by(SentimentScore.sentiment).all())
    positif = sent_rows.get("positif", 0)
    negatif = sent_rows.get("negatif", 0)
    netral = sent_rows.get("netral", 0)
    analyzed = positif + negatif + netral
    unanalyzed = max(0, total - analyzed)
    denom = analyzed or 1

    summary = SummaryStats(
        total_mentions=total,
        positif=positif,
        negatif=negatif,
        netral=netral,
        positif_pct=round(100 * positif / denom, 1),
        negatif_pct=round(100 * negatif / denom, 1),
        netral_pct=round(100 * netral / denom, 1),
        unanalyzed=unanalyzed,
    )

    # Trend by day
    day_expr = func.date(Post.posted_at)
    trend_q = (
        db.query(
            day_expr.label("day"),
            func.sum(case((SentimentScore.sentiment == "positif", 1), else_=0)).label("positif"),
            func.sum(case((SentimentScore.sentiment == "negatif", 1), else_=0)).label("negatif"),
            func.sum(case((SentimentScore.sentiment == "netral", 1), else_=0)).label("netral"),
            func.count(SentimentScore.id).label("total"),
        )
        .join(Post, SentimentScore.post_id == Post.id)
    )
    trend_q = _base_filters(trend_q, source, date_from, date_to, keyword, q)
    if sentiment:
        trend_q = trend_q.filter(SentimentScore.sentiment == sentiment)
    trend_rows = trend_q.group_by(day_expr).order_by(day_expr).all()
    trend = [
        TrendPoint(
            date=str(r.day),
            positif=int(r.positif or 0),
            negatif=int(r.negatif or 0),
            netral=int(r.netral or 0),
            total=int(r.total or 0),
        )
        for r in trend_rows
    ]

    # Platforms
    plat_q = (
        db.query(
            Post.source,
            func.count(Post.id).label("count"),
            func.sum(case((SentimentScore.sentiment == "positif", 1), else_=0)).label("positif"),
            func.sum(case((SentimentScore.sentiment == "negatif", 1), else_=0)).label("negatif"),
            func.sum(case((SentimentScore.sentiment == "netral", 1), else_=0)).label("netral"),
        )
        .outerjoin(SentimentScore)
    )
    plat_q = _base_filters(plat_q, source, date_from, date_to, keyword, q)
    if sentiment:
        plat_q = plat_q.filter(SentimentScore.sentiment == sentiment)
    platforms = [
        PlatformStat(
            source=r.source,
            count=int(r.count or 0),
            positif=int(r.positif or 0),
            negatif=int(r.negatif or 0),
            netral=int(r.netral or 0),
        )
        for r in plat_q.group_by(Post.source).order_by(func.count(Post.id).desc()).all()
    ]

    # Topics
    topic_q = (
        db.query(
            SentimentScore.topic_tag,
            func.count(SentimentScore.id).label("count"),
            func.sum(case((SentimentScore.sentiment == "positif", 1), else_=0)).label("positif"),
            func.sum(case((SentimentScore.sentiment == "negatif", 1), else_=0)).label("negatif"),
            func.sum(case((SentimentScore.sentiment == "netral", 1), else_=0)).label("netral"),
        )
        .join(Post)
        .filter(SentimentScore.topic_tag.isnot(None))
    )
    topic_q = _base_filters(topic_q, source, date_from, date_to, keyword, q)
    if sentiment:
        topic_q = topic_q.filter(SentimentScore.sentiment == sentiment)
    topics = [
        TopicStat(
            topic_tag=r.topic_tag or "umum",
            count=int(r.count or 0),
            positif=int(r.positif or 0),
            negatif=int(r.negatif or 0),
            netral=int(r.netral or 0),
        )
        for r in topic_q.group_by(SentimentScore.topic_tag)
        .order_by(func.count(SentimentScore.id).desc())
        .limit(15)
        .all()
    ]

    # Word cloud from recent texts
    text_q = _base_filters(db.query(Post.text_raw), source, date_from, date_to, keyword, q)
    if sentiment:
        text_q = text_q.join(SentimentScore).filter(SentimentScore.sentiment == sentiment)
    texts = [t[0] for t in text_q.order_by(Post.posted_at.desc()).limit(500).all()]
    counter: Counter = Counter()
    for text in texts:
        tokens = re.findall(r"[a-zA-ZÀ-ÿ]{3,}", text.lower())
        for tok in tokens:
            if tok not in STOPWORDS_ID and not tok.isdigit():
                counter[tok] += 1
    word_cloud = [
        WordFreq(word=w, count=c) for w, c in counter.most_common(60)
    ]

    return DashboardOverview(
        summary=summary,
        trend=trend,
        platforms=platforms,
        topics=topics,
        word_cloud=word_cloud,
    )


@router.get("/sna", response_model=SNAGraph)
def dashboard_sna(
    source: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    keyword: Optional[str] = None,
    sentiment: Optional[str] = None,
    q: Optional[str] = None,
    max_nodes: int = 120,
    db: Session = Depends(get_db),
):
    """Sentiment Network Analysis graph from authors, keywords, and topics."""
    data = build_sna_graph(
        db,
        source=source,
        date_from=date_from,
        date_to=date_to,
        keyword=keyword,
        sentiment=sentiment,
        q=q,
        max_nodes=min(max(max_nodes, 20), 200),
    )
    return SNAGraph(**data)

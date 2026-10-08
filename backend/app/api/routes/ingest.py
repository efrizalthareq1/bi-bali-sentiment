"""Keyword CRUD and ingest endpoints."""

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.instagram_hashtags import (
    HASHTAG_CATEGORY_LABELS,
    INSTAGRAM_PRIORITY_HASHTAGS,
    all_formatted_hashtags,
    format_hashtag,
)
from app.jobs.analyzer import analyze_pending_posts
from app.models import Keyword
from app.schemas import (
    HashtagCatalog,
    HashtagGroup,
    IgCommentDiagnostic,
    IgCommentSummary,
    IngestResult,
    KeywordCreate,
    KeywordOut,
    SeedResult,
)
from app.services.dummy_data import (
    generate_dummy_posts,
    generate_instagram_hashtag_demo,
    generate_outlook_demo,
    generate_tiktok_demo,
    seed_keywords,
)
from app.services.ingest_csv import ingest_upload_file
from app.services.news_scraper import sync_news

router = APIRouter(tags=["ingest"])


@router.get("/keywords", response_model=list[KeywordOut])
def list_keywords(
    category: str | None = None,
    hashtags_only: bool = False,
    db: Session = Depends(get_db),
):
    query = db.query(Keyword)
    if hashtags_only:
        query = query.filter(
            (Keyword.category.like("ig_%")) | (Keyword.keyword.like("#%"))
        )
    if category:
        query = query.filter(Keyword.category == category)
    return query.order_by(Keyword.category, Keyword.keyword).all()


@router.get("/hashtags", response_model=HashtagCatalog)
def list_hashtag_catalog(db: Session = Depends(get_db)):
    """Grouped Instagram hashtag catalog (seeded into keywords table)."""
    seed_keywords(db)
    rows = (
        db.query(Keyword)
        .filter((Keyword.category.like("ig_%")) | (Keyword.keyword.like("#%")))
        .order_by(Keyword.category, Keyword.keyword)
        .all()
    )
    grouped: dict[str, list[str]] = {}
    for row in rows:
        grouped.setdefault(row.category, []).append(row.keyword)

    if not grouped:
        for tag, category in all_formatted_hashtags():
            grouped.setdefault(category, []).append(tag)

    groups = [
        HashtagGroup(
            category=cat,
            label=HASHTAG_CATEGORY_LABELS.get(cat, cat),
            hashtags=tags,
        )
        for cat, tags in grouped.items()
    ]
    order = list(HASHTAG_CATEGORY_LABELS.keys())
    groups.sort(key=lambda g: order.index(g.category) if g.category in order else 99)

    return HashtagCatalog(
        total=sum(len(g.hashtags) for g in groups),
        priority_count=len(INSTAGRAM_PRIORITY_HASHTAGS),
        groups=groups,
    )


@router.post("/keywords", response_model=KeywordOut)
def create_keyword(payload: KeywordCreate, db: Session = Depends(get_db)):
    keyword = payload.keyword.strip()
    if payload.category.startswith("ig_") and not keyword.startswith("#"):
        keyword = format_hashtag(keyword)
    existing = db.query(Keyword).filter(Keyword.keyword == keyword).first()
    if existing:
        raise HTTPException(status_code=400, detail="Keyword sudah ada")
    row = Keyword(keyword=keyword, category=payload.category, active=payload.active)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.post("/ingest/upload", response_model=IngestResult)
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    try:
        inserted, skipped = ingest_upload_file(db, file.filename or "upload.csv", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return IngestResult(
        inserted=inserted,
        skipped=skipped,
        message=f"Berhasil impor {inserted} post, {skipped} dilewati.",
    )


@router.post("/ingest/news", response_model=IngestResult)
def ingest_news(
    max_keywords: int = Query(12, ge=1, le=40),
    per_keyword: int = Query(10, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """Fast Google News RSS sync (no slow URL decoder during ingest)."""
    from app.jobs.analyzer import analyze_pending_posts

    inserted, skipped = sync_news(
        db,
        per_keyword_limit=per_keyword,
        max_keywords=max_keywords,
    )
    analyzed = 0
    if inserted > 0:
        analyzed = analyze_pending_posts(db, batch_size=min(inserted, 50))
    return IngestResult(
        inserted=inserted,
        skipped=skipped,
        message=(
            f"Sinkron berita: {inserted} baru, {skipped} duplikat"
            + (f", {analyzed} dianalisis." if analyzed else ".")
        ),
    )


@router.post("/ingest/seed", response_model=SeedResult)
def seed_dummy(count: int = 180, db: Session = Depends(get_db)):
    keywords_created = seed_keywords(db)
    posts_created, analyzed = generate_dummy_posts(db, count=count, analyze=True)
    return SeedResult(
        posts_created=posts_created,
        keywords_created=keywords_created,
        analyzed=analyzed,
        message=f"Dummy data siap: {posts_created} post, {analyzed} dianalisis.",
    )


@router.post("/ingest/seed-hashtags", response_model=SeedResult)
def seed_hashtags_only(db: Session = Depends(get_db)):
    created = seed_keywords(db)
    total_ig = (
        db.query(Keyword)
        .filter((Keyword.category.like("ig_%")) | (Keyword.keyword.like("#%")))
        .count()
    )
    return SeedResult(
        posts_created=0,
        keywords_created=created,
        analyzed=0,
        message=f"Katalog hashtag siap. Baru: {created}, total IG hashtag di DB: {total_ig}.",
    )


@router.post("/ingest/instagram-demo", response_model=SeedResult)
def ingest_instagram_demo(
    per_hashtag: int = Query(3, ge=1, le=10),
    priority_only: bool = True,
    db: Session = Depends(get_db),
):
    """
    Generate demo Instagram posts for hashtag catalog (no API key required).
    For real posts, configure Graph API and call POST /sources/instagram/sync.
    """
    keywords_created = seed_keywords(db)
    if priority_only:
        tags = [format_hashtag(t) for t in INSTAGRAM_PRIORITY_HASHTAGS]
    else:
        tags = [t for t, _ in all_formatted_hashtags()]

    posts_created, analyzed = generate_instagram_hashtag_demo(
        db, per_hashtag=per_hashtag, analyze=True, hashtags=tags
    )
    return SeedResult(
        posts_created=posts_created,
        keywords_created=keywords_created,
        analyzed=analyzed,
        message=(
            f"Demo Instagram: {posts_created} post dari {len(tags)} hashtag "
            f"({analyzed} dianalisis)."
        ),
    )


@router.post("/ingest/tiktok-demo", response_model=SeedResult)
def ingest_tiktok_demo(
    count: int = Query(60, ge=10, le=200),
    db: Session = Depends(get_db),
):
    """Synthetic TikTok posts for dashboard testing (no Research API key)."""
    keywords_created = seed_keywords(db)
    posts_created, analyzed = generate_tiktok_demo(db, count=count, analyze=True)
    return SeedResult(
        posts_created=posts_created,
        keywords_created=keywords_created,
        analyzed=analyzed,
        message=f"Demo TikTok: {posts_created} post ({analyzed} dianalisis).",
    )


@router.post("/ingest/outlook-demo", response_model=SeedResult)
def ingest_outlook_demo(
    count: int = Query(40, ge=5, le=200),
    db: Session = Depends(get_db),
):
    """Synthetic Outlook emails for testing (no Azure / Graph credentials)."""
    keywords_created = seed_keywords(db)
    posts_created, analyzed = generate_outlook_demo(db, count=count, analyze=True)
    return SeedResult(
        posts_created=posts_created,
        keywords_created=keywords_created,
        analyzed=analyzed,
        message=f"Demo Outlook: {posts_created} email ({analyzed} dianalisis).",
    )


@router.post("/ingest/analyze-pending", response_model=IngestResult)
def trigger_analyze(batch_size: int = 50, db: Session = Depends(get_db)):
    n = analyze_pending_posts(db, batch_size=batch_size)
    return IngestResult(
        inserted=n,
        skipped=0,
        message=f"{n} post berhasil dianalisis.",
    )


@router.post("/ingest/purge-demos", response_model=IngestResult)
def purge_demos(db: Session = Depends(get_db)):
    from app.connectors import purge_demo_posts

    deleted = purge_demo_posts(db)
    return IngestResult(
        inserted=0,
        skipped=deleted,
        message=f"Data demo/placeholder dihapus: {deleted} post.",
    )


@router.post("/ingest/instagram-comments", response_model=IngestResult)
def ingest_instagram_comments(
    username: str = Query("qrissummerrun"),
    limit_posts: int = Query(12, ge=1, le=30),
    limit_comments: int = Query(40, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Tarik komentar netizen dari akun Instagram event (default @qrissummerrun)."""
    from app.services.instagram_comments import sync_account_comments

    inserted, skipped, analyzed, message = sync_account_comments(
        db,
        username=username,
        limit_posts=limit_posts,
        limit_comments=limit_comments,
    )
    return IngestResult(inserted=inserted, skipped=skipped, message=message)


@router.get("/ingest/instagram-comments/diagnostic", response_model=IgCommentDiagnostic)
def diagnose_instagram_comments(
    username: str = Query("qrissummerrun"),
):
    """Cek apakah cookie Instagram di Railway sudah terbaca & valid (bisa dibuka di browser)."""
    from app.services.instagram_comments import diagnose_instagram_session

    return IgCommentDiagnostic(**diagnose_instagram_session(username=username))


@router.get("/dashboard/instagram-comments", response_model=IgCommentSummary)
def get_instagram_comment_summary(
    username: str = Query("qrissummerrun"),
    db: Session = Depends(get_db),
):
    from app.services.instagram_comments import comment_sentiment_summary

    data = comment_sentiment_summary(db, username=username)
    return IgCommentSummary(**data)


@router.post("/ingest/instagram-comments/upload", response_model=IngestResult)
async def upload_instagram_comments_csv(
    file: UploadFile = File(...),
    username: str = Query("qrissummerrun"),
    db: Session = Depends(get_db),
):
    """Upload CSV komentar. Kolom: author/username, text/comment, url/post_url (opsional), posted_at (opsional)."""
    import csv
    import io

    from app.services.instagram_comments import ingest_comments_csv_rows

    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV kosong atau header tidak valid")
    inserted, skipped, analyzed = ingest_comments_csv_rows(db, rows, username=username)
    return IngestResult(
        inserted=inserted,
        skipped=skipped,
        message=(
            f"Upload komentar @{username.lstrip('@')}: {inserted} baru, "
            f"{skipped} dilewati, {analyzed} dianalisis."
        ),
    )

"""CSV/Excel upload ingestion."""

from __future__ import annotations

import io
from datetime import datetime
from typing import Optional

import pandas as pd
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Post

REQUIRED_COLUMNS = {"text_raw", "source"}
OPTIONAL_COLUMNS = {
    "source_post_id",
    "author",
    "url",
    "posted_at",
    "keyword_matched",
}


def _parse_datetime(value) -> datetime:
    if pd.isna(value) or value is None or value == "":
        return datetime.utcnow()
    if isinstance(value, datetime):
        return value
    parsed = pd.to_datetime(value, errors="coerce", utc=False)
    if pd.isna(parsed):
        return datetime.utcnow()
    return parsed.to_pydatetime()


def ingest_dataframe(db: Session, df: pd.DataFrame) -> tuple[int, int]:
    cols = {c.lower().strip(): c for c in df.columns}
    missing = REQUIRED_COLUMNS - set(cols.keys())
    if missing:
        raise ValueError(
            f"Kolom wajib hilang: {', '.join(sorted(missing))}. "
            f"Kolom tersedia: {', '.join(df.columns)}"
        )

    inserted = 0
    skipped = 0

    for idx, row in df.iterrows():
        text = str(row[cols["text_raw"]]).strip()
        source = str(row[cols["source"]]).strip().lower()
        if not text or text == "nan" or not source or source == "nan":
            skipped += 1
            continue

        source_post_id = (
            str(row[cols["source_post_id"]]).strip()
            if "source_post_id" in cols and not pd.isna(row[cols["source_post_id"]])
            else f"upload-{idx}-{hash(text) % 10_000_000}"
        )
        author = None
        if "author" in cols and not pd.isna(row[cols["author"]]):
            author = str(row[cols["author"]]).strip()
        url = None
        if "url" in cols and not pd.isna(row[cols["url"]]):
            url = str(row[cols["url"]]).strip()
        keyword_matched = None
        if "keyword_matched" in cols and not pd.isna(row[cols["keyword_matched"]]):
            keyword_matched = str(row[cols["keyword_matched"]]).strip()
        posted_at = (
            _parse_datetime(row[cols["posted_at"]])
            if "posted_at" in cols
            else datetime.utcnow()
        )

        post = Post(
            source=source,
            source_post_id=source_post_id,
            author=author,
            text_raw=text,
            url=url,
            posted_at=posted_at,
            keyword_matched=keyword_matched,
        )
        db.add(post)
        try:
            db.commit()
            inserted += 1
        except IntegrityError:
            db.rollback()
            skipped += 1

    return inserted, skipped


def ingest_upload_file(db: Session, filename: str, content: bytes) -> tuple[int, int]:
    lower = filename.lower()
    buffer = io.BytesIO(content)
    if lower.endswith(".csv"):
        df = pd.read_csv(buffer)
    elif lower.endswith((".xlsx", ".xls")):
        df = pd.read_excel(buffer)
    else:
        raise ValueError("Format tidak didukung. Gunakan CSV atau Excel (.xlsx).")
    return ingest_dataframe(db, df)

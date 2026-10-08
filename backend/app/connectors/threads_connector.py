"""Threads connector — percakapan netizen tentang BI (bukan akun resmi)."""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import List, Set
from urllib.parse import quote_plus

import feedparser

from app.connectors.base import BaseConnector, RawPost
from app.services.url_resolve import resolve_article_url

logger = logging.getLogger(__name__)

OFFICIAL_THREADS_ACCOUNTS: Set[str] = {
    "bankindonesia",
    "bank_indonesia",
    "bi_official",
    "bi_provinsibali",
}

BI_TERMS = (
    "bank indonesia",
    "bi-rate",
    "bi rate",
    "qris",
    "gpips",
    "gpib",
    "kpwbi",
    "bi bali",
    "rupiah",
    "inflasi",
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


def _extract_threads_author(url: str, fallback: str | None = None) -> str | None:
    match = re.search(r"threads\.net/@([^/]+)", url or "")
    if match:
        return match.group(1)
    return fallback


class ThreadsConnector(BaseConnector):
    id = "threads"
    name = "Threads"
    description = (
        "Postingan Threads netizen yang membahas Bank Indonesia / isu kebijakan "
        "(bukan akun resmi @bankindonesia)."
    )
    requires_api_key = False

    def is_configured(self) -> bool:
        return True

    def fetch_posts(self, keywords: List[str], limit: int = 50) -> List[RawPost]:
        results = self._fetch_via_google_news(keywords, limit=limit)
        clean: List[RawPost] = []
        seen: set[str] = set()
        for p in results:
            author = (p.author or "").lower().lstrip("@")
            if author in OFFICIAL_THREADS_ACCOUNTS:
                continue
            if p.source_post_id.startswith("profile-"):
                continue
            if "threads.net" not in (p.url or "") and "threads.com" not in (p.url or ""):
                continue
            if p.source_post_id in seen:
                continue
            seen.add(p.source_post_id)
            clean.append(p)
        return clean[:limit]

    def _fetch_via_google_news(self, keywords: List[str], limit: int) -> List[RawPost]:
        keys = [k for k in keywords if k and not str(k).startswith("#")][:8] or [
            "Bank Indonesia Aceh",
            "BI Aceh",
            "QRIS Aceh",
            "inflasi Aceh",
            "UMKM Aceh",
            "KPwBI Aceh",
            "Banda Aceh",
        ]
        for extra in ("Bank Indonesia Aceh", "QRIS Aceh", "inflasi Aceh", "Meuseuraya"):
            if extra not in keys:
                keys.append(extra)

        results: List[RawPost] = []
        seen: set[str] = set()
        resolve_budget = 25

        queries = [f'"{kw}" site:threads.net' for kw in keys[:6]]
        queries.extend(
            [
                '"Bank Indonesia Aceh" OR "BI Aceh" site:threads.net',
                '"QRIS Aceh" OR InflasiAceh site:threads.net',
                "UMKMAceh OR Meuseuraya site:threads.net",
                '"Banda Aceh" (Bank Indonesia OR BI OR QRIS) site:threads.net',
            ]
        )

        for q in queries:
            if len(results) >= limit:
                break
            url = (
                "https://news.google.com/rss/search?"
                f"q={quote_plus(q)}&hl=id&gl=ID&ceid=ID:id"
            )
            try:
                feed = feedparser.parse(url)
            except Exception as exc:
                logger.warning("Threads RSS failed for %s: %s", q, exc)
                continue

            for entry in feed.entries:
                if len(results) >= limit:
                    break
                title = getattr(entry, "title", "") or ""
                summary = getattr(entry, "summary", "") or ""
                link = getattr(entry, "link", "") or ""
                blob = f"{title}\n{summary}\n{link}"
                lowered = blob.lower()

                if not any(t in lowered for t in BI_TERMS):
                    continue

                resolved = None
                m = re.search(
                    r"https?://(?:www\.)?threads\.(?:net|com)/@[^\s\"'<>]+(?:/post/[^\s\"'<>]+)?",
                    blob,
                    re.I,
                )
                if m:
                    resolved = m.group(0).rstrip(".,)")
                elif resolve_budget > 0:
                    resolve_budget -= 1
                    try:
                        candidate = resolve_article_url(link, fast=False) or ""
                    except Exception:
                        candidate = ""
                    if "threads.net" in candidate or "threads.com" in candidate:
                        resolved = candidate

                if not resolved:
                    continue
                if "threads.net" not in resolved and "threads.com" not in resolved:
                    continue

                clean = re.sub(r"<[^>]+>", " ", summary)
                clean = clean.replace("&nbsp;", " ")
                clean = re.sub(r"\s+", " ", clean).strip()
                text = title if not clean else f"{title}. {clean}"

                source_id = hashlib.sha256(f"{resolved}|{title}".encode()).hexdigest()[:32]
                if source_id in seen:
                    continue
                seen.add(source_id)

                src = getattr(entry, "source", None)
                fallback_author = src.get("title") if isinstance(src, dict) else None
                author = _extract_threads_author(resolved, fallback_author)
                handle_m = re.search(r"@([A-Za-z0-9_\.]{2,30})", title)
                if handle_m and not author:
                    author = handle_m.group(1)
                if author and author.lower().lstrip("@") in OFFICIAL_THREADS_ACCOUNTS:
                    continue

                matched = next(
                    (k for k in keys if k.lower() in text.lower()),
                    keys[0],
                )
                results.append(
                    RawPost(
                        source="threads",
                        source_post_id=source_id,
                        author=author or "netizen_threads",
                        text_raw=text[:5000],
                        url=resolved,
                        posted_at=_parse_entry_date(entry),
                        keyword_matched=matched,
                    )
                )
        return results

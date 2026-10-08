"""Instagram connector — hashtag netizen (Graph API) + pencarian publik site:instagram.com."""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional, Set
from urllib.parse import quote_plus

import feedparser
import httpx

from app.config import get_settings
from app.connectors.base import BaseConnector, RawPost
from app.instagram_hashtags import (
    INSTAGRAM_PRIORITY_HASHTAGS,
    format_hashtag,
    priority_formatted_hashtags,
)
from app.services.url_resolve import resolve_article_url

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.facebook.com/v21.0"

OFFICIAL_IG_HINTS: Set[str] = {
    "bankindonesia",
    "bank_indonesia",
    "bi_official",
    "bank indonesia",
}


class InstagramConnector(BaseConnector):
    id = "instagram"
    name = "Instagram"
    description = (
        "Postingan netizen Instagram yang membahas BI (hashtag Graph API jika dikonfigurasi, "
        "atau indeks publik site:instagram.com). Bukan feed akun resmi BI."
    )
    requires_api_key = True

    def is_configured(self) -> bool:
        # Always "ready" for public index; Graph API is optional enhancement
        return True

    def get_info(self, post_count: int = 0, last_sync=None):
        s = get_settings()
        has_api = bool(s.instagram_access_token and s.instagram_business_account_id)
        info = super().get_info(post_count=post_count, last_sync=last_sync)
        info.requires_api_key = True
        info.configured = True
        info.status = "connected" if has_api else "ready"
        info.description = (
            "Mode Graph API hashtag (netizen) aktif."
            if has_api
            else (
                "Mode publik: postingan Instagram terindeks yang membahas Bank Indonesia / "
                "QRIS / inflasi (bukan akun resmi BI). Isi token untuk hashtag Graph API."
            )
        )
        return info

    def _headers_params(self) -> dict:
        return {"access_token": get_settings().instagram_access_token}

    def _has_graph_api(self) -> bool:
        s = get_settings()
        return bool(s.instagram_access_token and s.instagram_business_account_id)

    def resolve_hashtag_id(self, client: httpx.Client, hashtag: str) -> Optional[str]:
        settings = get_settings()
        name = hashtag.lstrip("#")
        resp = client.get(
            f"{GRAPH_BASE}/ig_hashtag_search",
            params={
                **self._headers_params(),
                "user_id": settings.instagram_business_account_id,
                "q": name,
            },
        )
        if resp.status_code != 200:
            logger.warning(
                "Hashtag search failed for #%s: %s %s",
                name,
                resp.status_code,
                resp.text[:300],
            )
            return None
        data = resp.json().get("data") or []
        if not data:
            return None
        return data[0].get("id")

    def fetch_recent_media(
        self,
        client: httpx.Client,
        hashtag_id: str,
        limit: int = 25,
    ) -> List[dict]:
        settings = get_settings()
        resp = client.get(
            f"{GRAPH_BASE}/{hashtag_id}/recent_media",
            params={
                **self._headers_params(),
                "user_id": settings.instagram_business_account_id,
                "fields": "id,caption,permalink,timestamp,media_type,like_count,comments_count",
                "limit": min(limit, 50),
            },
        )
        if resp.status_code != 200:
            logger.warning(
                "recent_media failed for %s: %s %s",
                hashtag_id,
                resp.status_code,
                resp.text[:300],
            )
            return []
        return resp.json().get("data") or []

    def _normalize_hashtags(self, keywords: List[str]) -> List[str]:
        tags = []
        for kw in keywords:
            kw = kw.strip()
            if not kw:
                continue
            if kw.startswith("#"):
                tags.append(kw)
            elif kw.replace(" ", "") in INSTAGRAM_PRIORITY_HASHTAGS or any(
                kw.lower() == t.lower() for t in INSTAGRAM_PRIORITY_HASHTAGS
            ):
                tags.append(format_hashtag(kw))
        if tags:
            return tags
        return priority_formatted_hashtags(
            limit=get_settings().instagram_hashtag_sync_limit
        )

    def fetch_posts(self, keywords: List[str], limit: int = 50) -> List[RawPost]:
        posts: List[RawPost] = []
        if self._has_graph_api():
            try:
                posts.extend(self._fetch_via_graph(keywords, limit=limit))
            except Exception as exc:
                logger.warning("Instagram Graph API failed: %s", exc)

        remaining = max(0, limit - len(posts))
        if remaining:
            posts.extend(self._fetch_via_public_index(keywords, limit=remaining))

        clean: List[RawPost] = []
        seen: set[str] = set()
        for p in posts:
            blob = f"{p.author or ''} {p.url or ''} {p.text_raw or ''}".lower()
            if any(h in blob for h in OFFICIAL_IG_HINTS) and "bankindonesia" in (p.url or "").lower():
                # skip clear official profile posts
                if "/p/" not in (p.url or "") and "/reel/" not in (p.url or ""):
                    continue
            if p.source_post_id in seen:
                continue
            seen.add(p.source_post_id)
            clean.append(p)
        return clean[:limit]

    def _fetch_via_graph(self, keywords: List[str], limit: int) -> List[RawPost]:
        hashtags = self._normalize_hashtags(keywords)
        sync_limit = get_settings().instagram_hashtag_sync_limit
        hashtags = hashtags[:sync_limit]
        per_tag = max(1, limit // max(len(hashtags), 1))
        seen_ids: Dict[str, bool] = {}
        posts: List[RawPost] = []

        with httpx.Client(timeout=45.0) as client:
            for tag in hashtags:
                hashtag_id = self.resolve_hashtag_id(client, tag)
                if not hashtag_id:
                    continue
                media = self.fetch_recent_media(client, hashtag_id, limit=per_tag)
                for item in media:
                    media_id = str(item.get("id") or "")
                    if not media_id or media_id in seen_ids:
                        continue
                    seen_ids[media_id] = True

                    caption = (item.get("caption") or "").strip()
                    if not caption:
                        caption = f"Post Instagram tanpa caption ({tag})"

                    ts = item.get("timestamp")
                    if ts:
                        try:
                            posted_at = datetime.fromisoformat(
                                ts.replace("Z", "+00:00")
                            ).replace(tzinfo=None)
                        except ValueError:
                            posted_at = datetime.utcnow()
                    else:
                        posted_at = datetime.utcnow()

                    posts.append(
                        RawPost(
                            source="instagram",
                            source_post_id=media_id,
                            author=None,
                            text_raw=caption[:5000],
                            url=item.get("permalink"),
                            posted_at=posted_at,
                            keyword_matched=tag,
                        )
                    )
                    if len(posts) >= limit:
                        return posts
        return posts

    def _fetch_via_public_index(self, keywords: List[str], limit: int) -> List[RawPost]:
        keys = [k for k in keywords if k and not str(k).startswith("ig_")][:8] or [
            "Bank Indonesia Aceh",
            "BI Aceh",
            "KPwBI Aceh",
            "QRIS Aceh",
            "inflasi Aceh",
            "UMKM Aceh",
            "Banda Aceh",
        ]
        queries = [f'"{kw}" site:instagram.com' for kw in keys[:6]]
        queries.extend(
            [
                '"Bank Indonesia Aceh" OR "BI Aceh" OR KPwBIAceh site:instagram.com',
                '"QRIS Aceh" OR QRISAceh site:instagram.com',
                '"inflasi Aceh" OR TPIDAceh site:instagram.com',
                "Meuseuraya OR UMKMAceh site:instagram.com",
            ]
        )

        results: List[RawPost] = []
        seen: set[str] = set()

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
                logger.warning("Instagram public RSS failed: %s", exc)
                continue

            for entry in feed.entries:
                if len(results) >= limit:
                    break
                title = getattr(entry, "title", "") or ""
                summary = getattr(entry, "summary", "") or ""
                link = getattr(entry, "link", "") or ""
                blob = f"{title}\n{summary}\n{link}"

                resolved = None
                m = re.search(
                    r"https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/[^\s\"'<>]+",
                    blob,
                    re.I,
                )
                if m:
                    resolved = m.group(0).rstrip(".,)/")
                elif len(results) < 8:
                    try:
                        candidate = resolve_article_url(link) or ""
                    except Exception:
                        candidate = ""
                    if "instagram.com" in candidate:
                        resolved = candidate

                if not resolved or "instagram.com" not in resolved:
                    continue
                # skip bare official profile pages
                if re.search(r"instagram\.com/(bankindonesia|bank_indonesia)/?$", resolved, re.I):
                    continue

                clean = re.sub(r"<[^>]+>", " ", summary)
                clean = re.sub(r"\s+", " ", clean).strip()
                text = title if not clean else f"{title}. {clean}"
                source_id = hashlib.sha256(f"{resolved}|{title}".encode()).hexdigest()[:32]
                if source_id in seen:
                    continue
                seen.add(source_id)

                posted_at = datetime.utcnow()
                for attr in ("published", "updated"):
                    raw = getattr(entry, attr, None)
                    if raw:
                        try:
                            dt = parsedate_to_datetime(raw)
                            if dt.tzinfo:
                                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                            posted_at = dt
                            break
                        except (TypeError, ValueError, IndexError):
                            pass

                matched = next((k for k in keys if k.lower() in text.lower()), keys[0])
                results.append(
                    RawPost(
                        source="instagram",
                        source_post_id=source_id,
                        author=None,
                        text_raw=text[:5000],
                        url=resolved,
                        posted_at=posted_at,
                        keyword_matched=matched,
                    )
                )
        return results

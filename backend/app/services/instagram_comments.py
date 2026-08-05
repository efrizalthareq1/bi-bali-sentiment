"""Fetch Instagram post comments for a monitored account (e.g. @qrissummerrun).

Priority:
1. Meta Graph API — when INSTAGRAM_ACCESS_TOKEN + BUSINESS_ACCOUNT_ID are set
   and the connected IG user owns the media (best for official event accounts).
2. Optional session cookie INSTAGRAM_SESSION_ID — public media comments endpoint.
3. Otherwise returns empty; UI supports CSV upload of comments.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import List, Optional, Tuple

import httpx
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.connectors.base import RawPost
from app.jobs.analyzer import analyze_pending_posts
from app.models import Post, SentimentScore

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.facebook.com/v21.0"
DEFAULT_MONITOR_USERNAME = "qrissummerrun"
COMMENT_SOURCE = "instagram_comment"
ACCOUNT_KEYWORD = "@qrissummerrun"


def _parse_ig_timestamp(raw: Optional[str]) -> datetime:
    if not raw:
        return datetime.utcnow()
    try:
        # Graph: 2024-01-01T12:00:00+0000
        cleaned = raw.replace("+0000", "+00:00")
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1] + "+00:00"
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except ValueError:
        try:
            return datetime.utcfromtimestamp(int(raw))
        except (TypeError, ValueError):
            return datetime.utcnow()


def _comment_source_id(comment_id: str) -> str:
    return f"igc-{comment_id}"


class InstagramCommentFetcher:
    def __init__(self, username: str = DEFAULT_MONITOR_USERNAME):
        self.username = username.lstrip("@").strip() or DEFAULT_MONITOR_USERNAME
        self.settings = get_settings()
        self.last_hint: str = ""

    def _session_headers(self, csrf_token: str) -> dict:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "X-IG-App-ID": "936619743392459",
            "X-ASBD-ID": "129477",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"https://www.instagram.com/{self.username}/",
            "Origin": "https://www.instagram.com",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }
        if csrf_token:
            headers["X-CSRFToken"] = csrf_token
        return headers

    def _session_cookies(self, session_id: str, csrf_token: str) -> dict:
        cookies = {"sessionid": session_id}
        if csrf_token:
            cookies["csrftoken"] = csrf_token
        ds_user = (self.settings.instagram_ds_user_id or "").strip()
        if ds_user:
            cookies["ds_user_id"] = ds_user
        return cookies

    def fetch_comment_posts(self, limit_posts: int = 12, limit_comments: int = 40) -> List[RawPost]:
        posts: List[RawPost] = []
        self.last_hint = ""
        if self._has_graph():
            try:
                posts = self._fetch_via_graph(limit_posts, limit_comments)
                if posts:
                    return posts
            except Exception as exc:
                logger.warning("Graph comment fetch failed: %s", exc)
                self.last_hint = f"Graph API gagal: {exc}"

        session_id = (self.settings.instagram_session_id or "").strip()
        csrf = (self.settings.instagram_csrf_token or "").strip()
        if not session_id:
            self.last_hint = (
                "INSTAGRAM_SESSION_ID belum terdeteksi di server. "
                "Pastikan variable ada di service api Railway, lalu redeploy."
            )
            return []
        try:
            posts, hint = self._fetch_via_session(session_id, csrf, limit_posts, limit_comments)
            if hint:
                self.last_hint = hint
            return posts
        except Exception as exc:
            logger.warning("Session comment fetch failed: %s", exc)
            self.last_hint = f"Error saat fetch komentar: {exc}"
            return []

    def _has_graph(self) -> bool:
        return bool(
            self.settings.instagram_access_token
            and self.settings.instagram_business_account_id
        )

    def _token_params(self) -> dict:
        return {"access_token": self.settings.instagram_access_token}

    def _fetch_via_graph(self, limit_posts: int, limit_comments: int) -> List[RawPost]:
        ig_user = self.settings.instagram_business_account_id
        fields = (
            "id,caption,permalink,timestamp,username,"
            f"comments.limit({min(limit_comments, 50)}){{id,text,username,timestamp,from}}"
        )
        results: List[RawPost] = []

        with httpx.Client(timeout=45.0) as client:
            # 1) Own media (if connected account IS qrissummerrun)
            media = self._graph_own_media(client, ig_user, fields, limit_posts)
            # 2) Business discovery fallback for other business username
            if not media:
                media = self._graph_business_discovery(client, ig_user, fields, limit_posts)

            for item in media:
                permalink = item.get("permalink") or f"https://www.instagram.com/{self.username}/"
                caption = (item.get("caption") or "").strip()
                media_ts = _parse_ig_timestamp(item.get("timestamp"))
                media_id = str(item.get("id") or "")

                # Store parent post snapshot (optional context)
                if media_id and caption:
                    results.append(
                        RawPost(
                            source="instagram",
                            source_post_id=f"igpost-{media_id}",
                            author=item.get("username") or self.username,
                            text_raw=caption[:5000],
                            url=permalink,
                            posted_at=media_ts,
                            keyword_matched=ACCOUNT_KEYWORD,
                        )
                    )

                comments = (item.get("comments") or {}).get("data") or []
                for c in comments:
                    text = (c.get("text") or "").strip()
                    if not text:
                        continue
                    cid = str(c.get("id") or "")
                    if not cid:
                        cid = hashlib.sha256(f"{media_id}|{text}".encode()).hexdigest()[:24]
                    from_user = None
                    if isinstance(c.get("from"), dict):
                        from_user = c["from"].get("username")
                    author = from_user or c.get("username") or "netizen_ig"
                    results.append(
                        RawPost(
                            source=COMMENT_SOURCE,
                            source_post_id=_comment_source_id(cid),
                            author=author,
                            text_raw=text[:5000],
                            url=permalink,
                            posted_at=_parse_ig_timestamp(c.get("timestamp")) or media_ts,
                            keyword_matched=ACCOUNT_KEYWORD,
                        )
                    )
        return results

    def _graph_own_media(
        self, client: httpx.Client, ig_user: str, fields: str, limit_posts: int
    ) -> List[dict]:
        resp = client.get(
            f"{GRAPH_BASE}/{ig_user}/media",
            params={**self._token_params(), "fields": fields, "limit": min(limit_posts, 25)},
        )
        if resp.status_code != 200:
            logger.info("Own media failed: %s %s", resp.status_code, resp.text[:200])
            return []
        data = resp.json().get("data") or []
        # If username filter set, only keep matching username when present
        filtered = []
        for item in data:
            uname = (item.get("username") or "").lower()
            if uname and uname != self.username.lower():
                continue
            filtered.append(item)
        return filtered or data

    def _graph_business_discovery(
        self, client: httpx.Client, ig_user: str, fields: str, limit_posts: int
    ) -> List[dict]:
        # Nested media fields for discovery
        media_fields = (
            "id,caption,permalink,timestamp,username,"
            f"comments.limit({50}){{id,text,username,timestamp}}"
        )
        q = (
            f"business_discovery.username({self.username})"
            f"{{username,media.limit({min(limit_posts, 25)}){{{media_fields}}}}}"
        )
        resp = client.get(
            f"{GRAPH_BASE}/{ig_user}",
            params={**self._token_params(), "fields": q},
        )
        if resp.status_code != 200:
            logger.info(
                "Business discovery failed for @%s: %s %s",
                self.username,
                resp.status_code,
                resp.text[:300],
            )
            return []
        discovery = resp.json().get("business_discovery") or {}
        media = (discovery.get("media") or {}).get("data") or []
        return media

    def _fetch_via_session(
        self, session_id: str, csrf_token: str, limit_posts: int, limit_comments: int
    ) -> Tuple[List[RawPost], str]:
        """Fetch comments via Instagram web API using sessionid cookie (Opsi B)."""
        headers = self._session_headers(csrf_token)
        cookies = self._session_cookies(session_id, csrf_token)
        results: List[RawPost] = []
        hint = ""

        with httpx.Client(timeout=40.0, headers=headers, cookies=cookies, follow_redirects=True) as client:
            # Warm session (Instagram sometimes requires landing on profile first)
            warm = client.get(f"https://www.instagram.com/{self.username}/")
            if warm.status_code not in (200, 302):
                logger.warning("Profile warm-up status %s", warm.status_code)

            profile = client.get(
                "https://www.instagram.com/api/v1/users/web_profile_info/",
                params={"username": self.username},
            )
            if profile.status_code != 200:
                body_preview = profile.text[:300]
                try:
                    err_msg = (profile.json().get("message") or body_preview).strip()
                except Exception:
                    err_msg = body_preview
                logger.warning(
                    "Profile fetch status %s body=%s",
                    profile.status_code,
                    body_preview,
                )
                if profile.status_code in (401, 403):
                    hint = (
                        f"Instagram menolak session (HTTP {profile.status_code}): {err_msg}. "
                        "Cookie sessionid/csrftoken kedaluwarsa atau salah salin. "
                        "Login ulang di browser → salin ulang cookie → update Railway → redeploy api."
                    )
                elif profile.status_code == 429:
                    hint = "Instagram rate limit (HTTP 429). Coba lagi 10–30 menit kemudian."
                else:
                    hint = (
                        f"Gagal ambil profil @{self.username} (HTTP {profile.status_code}): {err_msg}. "
                        "Cek cookie atau coba tambahkan INSTAGRAM_DS_USER_ID dari browser."
                    )
                return [], hint

            user = ((profile.json().get("data") or {}).get("user") or {})
            if not user:
                return [], (
                    f"Profil @{self.username} tidak ditemukan di respons Instagram. "
                    "Periksa username atau status akun."
                )

            edges = ((user.get("edge_owner_to_timeline_media") or {}).get("edges") or [])[
                :limit_posts
            ]
            if not edges:
                return [], (
                    f"Akun @{self.username} ditemukan tapi tidak ada postingan publik yang bisa dibaca. "
                    "Pastikan akun tidak private atau postingan tersedia."
                )

            comments_ok = 0
            comments_blocked = False
            for edge in edges:
                node = edge.get("node") or {}
                shortcode = node.get("shortcode")
                media_id = str(node.get("id") or "")
                permalink = (
                    f"https://www.instagram.com/p/{shortcode}/"
                    if shortcode
                    else f"https://www.instagram.com/{self.username}/"
                )
                caption_edges = (
                    (node.get("edge_media_to_caption") or {}).get("edges") or []
                )
                caption = ""
                if caption_edges:
                    caption = ((caption_edges[0].get("node") or {}).get("text") or "").strip()
                taken = node.get("taken_at_timestamp")
                media_ts = (
                    datetime.utcfromtimestamp(int(taken))
                    if taken
                    else datetime.utcnow()
                )
                if media_id and caption:
                    results.append(
                        RawPost(
                            source="instagram",
                            source_post_id=f"igpost-{media_id}",
                            author=self.username,
                            text_raw=caption[:5000],
                            url=permalink,
                            posted_at=media_ts,
                            keyword_matched=ACCOUNT_KEYWORD,
                        )
                    )

                if not media_id:
                    continue
                c_resp = client.get(
                    f"https://www.instagram.com/api/v1/media/{media_id}/comments/",
                    params={"can_support_threading": "true"},
                )
                if c_resp.status_code != 200:
                    if c_resp.status_code in (401, 403):
                        comments_blocked = True
                    continue
                batch = (c_resp.json().get("comments") or [])[:limit_comments]
                comments_ok += len(batch)
                for c in batch:
                    text = (c.get("text") or "").strip()
                    if not text:
                        continue
                    cid = str(c.get("pk") or c.get("id") or "")
                    user_obj = c.get("user") or {}
                    author = user_obj.get("username") or "netizen_ig"
                    created = c.get("created_at") or c.get("created_at_utc")
                    results.append(
                        RawPost(
                            source=COMMENT_SOURCE,
                            source_post_id=_comment_source_id(cid or hashlib.sha256(text.encode()).hexdigest()[:16]),
                            author=author,
                            text_raw=text[:5000],
                            url=permalink,
                            posted_at=_parse_ig_timestamp(str(created) if created else None) or media_ts,
                            keyword_matched=ACCOUNT_KEYWORD,
                        )
                    )
        comment_posts = [p for p in results if p.source == COMMENT_SOURCE]
        if not comment_posts:
            if comments_blocked:
                hint = (
                    "Postingan ditemukan tapi Instagram menolak akses komentar (401/403). "
                    "Salin ulang sessionid + csrftoken (+ ds_user_id) dari browser, "
                    "atau gunakan akun IG yang bisa melihat komentar @qrissummerrun."
                )
            else:
                hint = (
                    f"Ditemukan {len(edges)} postingan tapi 0 komentar. "
                    "Mungkin belum ada komentar publik atau komentar dinonaktifkan."
                )
        return results, hint


def diagnose_instagram_session(username: str = DEFAULT_MONITOR_USERNAME) -> dict:
    """Check whether Railway cookies work — safe to expose (no secret values)."""
    fetcher = InstagramCommentFetcher(username=username)
    settings = fetcher.settings
    session_id = (settings.instagram_session_id or "").strip()
    csrf = (settings.instagram_csrf_token or "").strip()
    ds_user = (settings.instagram_ds_user_id or "").strip()

    out = {
        "username": fetcher.username,
        "session_configured": bool(session_id),
        "session_id_length": len(session_id),
        "csrf_configured": bool(csrf),
        "ds_user_id_configured": bool(ds_user),
        "graph_api_configured": fetcher._has_graph(),
        "profile_status": None,
        "profile_message": "",
        "media_posts_found": 0,
        "comments_status": None,
        "comments_found_sample": 0,
        "ok": False,
        "hint": "",
    }

    if not session_id and not fetcher._has_graph():
        out["hint"] = (
            "INSTAGRAM_SESSION_ID belum terdeteksi di server api. "
            "Tambahkan di Railway → service api → Variables → redeploy."
        )
        return out

    if not session_id:
        out["hint"] = "Graph API dikonfigurasi tapi tidak mengembalikan data. Cek token Business."
        return out

    headers = fetcher._session_headers(csrf)
    cookies = fetcher._session_cookies(session_id, csrf)
    try:
        with httpx.Client(timeout=35.0, headers=headers, cookies=cookies, follow_redirects=True) as client:
            client.get(f"https://www.instagram.com/{fetcher.username}/")
            profile = client.get(
                "https://www.instagram.com/api/v1/users/web_profile_info/",
                params={"username": fetcher.username},
            )
            out["profile_status"] = profile.status_code
            try:
                payload = profile.json()
                out["profile_message"] = (payload.get("message") or "")[:200]
            except Exception:
                out["profile_message"] = profile.text[:200]

            if profile.status_code != 200:
                if profile.status_code in (401, 403):
                    out["hint"] = (
                        "Cookie ditolak Instagram — salin ulang sessionid & csrftoken "
                        "(login ulang di browser), update Railway, redeploy api."
                    )
                elif profile.status_code == 429:
                    out["hint"] = "Rate limit Instagram. Coba lagi nanti."
                else:
                    out["hint"] = (
                        f"HTTP {profile.status_code} dari Instagram. "
                        "Cek cookie atau tambahkan INSTAGRAM_DS_USER_ID."
                    )
                return out

            user = ((profile.json().get("data") or {}).get("user") or {})
            edges = ((user.get("edge_owner_to_timeline_media") or {}).get("edges") or [])
            out["media_posts_found"] = len(edges)
            if not edges:
                out["hint"] = "Profil OK tapi tidak ada postingan yang bisa dibaca."
                return out

            media_id = str((edges[0].get("node") or {}).get("id") or "")
            if media_id:
                c_resp = client.get(
                    f"https://www.instagram.com/api/v1/media/{media_id}/comments/",
                    params={"can_support_threading": "true"},
                )
                out["comments_status"] = c_resp.status_code
                if c_resp.status_code == 200:
                    out["comments_found_sample"] = len(c_resp.json().get("comments") or [])
                else:
                    try:
                        out["profile_message"] = (c_resp.json().get("message") or c_resp.text[:200])
                    except Exception:
                        out["profile_message"] = c_resp.text[:200]

            if out["comments_found_sample"] > 0:
                out["ok"] = True
                out["hint"] = "Cookie valid. Jalankan POST /ingest/instagram-comments untuk sinkronisasi."
            elif out.get("comments_status") in (401, 403):
                out["hint"] = (
                    "Profil terbaca tapi komentar ditolak. Tambahkan INSTAGRAM_DS_USER_ID "
                    "dari cookie browser, atau gunakan akun IG lain."
                )
            else:
                out["hint"] = "Profil terbaca; komentar 0 atau endpoint komentar tidak mengembalikan data."
    except Exception as exc:
        out["hint"] = f"Error koneksi ke Instagram: {exc}"

    return out


def persist_and_analyze(db: Session, raw_posts: List[RawPost]) -> Tuple[int, int, int]:
    inserted = 0
    skipped = 0
    for raw in raw_posts:
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
    analyzed = 0
    if inserted:
        analyzed = analyze_pending_posts(db, batch_size=min(inserted + 50, 200))
    return inserted, skipped, analyzed


def sync_account_comments(
    db: Session,
    username: str = DEFAULT_MONITOR_USERNAME,
    limit_posts: int = 12,
    limit_comments: int = 40,
) -> Tuple[int, int, int, str]:
    fetcher = InstagramCommentFetcher(username=username)
    raw = fetcher.fetch_comment_posts(limit_posts=limit_posts, limit_comments=limit_comments)
    comments = [p for p in raw if p.source == COMMENT_SOURCE]
    if not raw:
        hint = fetcher.last_hint or (
            f"Tidak ada komentar asli yang bisa diambil untuk @{fetcher.username}. "
            "Set INSTAGRAM_SESSION_ID (+ INSTAGRAM_CSRF_TOKEN) di Railway service api, redeploy, "
            "lalu cek GET /ingest/instagram-comments/diagnostic"
        )
        return (0, 0, 0, hint)
    inserted, skipped, analyzed = persist_and_analyze(db, raw)
    return (
        inserted,
        skipped,
        analyzed,
        (
            f"@{fetcher.username}: {inserted} baru ({len(comments)} komentar dalam batch), "
            f"{skipped} dilewati, {analyzed} dianalisis."
        ),
    )


def comment_sentiment_summary(db: Session, username: str = DEFAULT_MONITOR_USERNAME) -> dict:
    keyword = f"@{username.lstrip('@')}"
    rows = (
        db.query(Post)
        .outerjoin(SentimentScore)
        .filter(Post.source == COMMENT_SOURCE)
        .filter(Post.keyword_matched == keyword)
        .order_by(Post.posted_at.desc())
        .limit(200)
        .all()
    )
    pos = neg = neu = unanalyzed = 0
    items = []
    for p in rows:
        s = p.sentiment.sentiment if p.sentiment else None
        if s == "positif":
            pos += 1
        elif s == "negatif":
            neg += 1
        elif s == "netral":
            neu += 1
        else:
            unanalyzed += 1
        items.append(
            {
                "id": p.id,
                "author": p.author,
                "text_raw": p.text_raw,
                "url": p.url,
                "posted_at": p.posted_at.isoformat() if p.posted_at else None,
                "sentiment": s,
                "confidence": p.sentiment.confidence if p.sentiment else None,
            }
        )
    total = pos + neg + neu
    def pct(n: int) -> float:
        return round((n / total) * 100, 1) if total else 0.0

    return {
        "username": username.lstrip("@"),
        "profile_url": f"https://www.instagram.com/{username.lstrip('@')}/",
        "total_comments": len(rows),
        "positif": pos,
        "negatif": neg,
        "netral": neu,
        "unanalyzed": unanalyzed,
        "positif_pct": pct(pos),
        "negatif_pct": pct(neg),
        "netral_pct": pct(neu),
        "items": items[:50],
    }


def ingest_comments_csv_rows(
    db: Session,
    rows: List[dict],
    username: str = DEFAULT_MONITOR_USERNAME,
) -> Tuple[int, int, int]:
    """rows: author, text, url?, posted_at?"""
    keyword = f"@{username.lstrip('@')}"
    raw: List[RawPost] = []
    for i, row in enumerate(rows):
        text = (row.get("text") or row.get("text_raw") or row.get("comment") or "").strip()
        if not text:
            continue
        author = (row.get("author") or row.get("username") or "netizen_ig").strip()
        url = (row.get("url") or row.get("post_url") or f"https://www.instagram.com/{username}/").strip()
        posted_at = datetime.utcnow()
        raw_date = row.get("posted_at") or row.get("date")
        if raw_date:
            try:
                posted_at = datetime.fromisoformat(str(raw_date).replace("Z", ""))
            except ValueError:
                pass
        sid = hashlib.sha256(f"{author}|{text}|{url}".encode()).hexdigest()[:28]
        raw.append(
            RawPost(
                source=COMMENT_SOURCE,
                source_post_id=_comment_source_id(sid),
                author=author,
                text_raw=text[:5000],
                url=url,
                posted_at=posted_at,
                keyword_matched=keyword,
            )
        )
    return persist_and_analyze(db, raw)

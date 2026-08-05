"""TikTok connector via Research API (client credentials + video query)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import List, Optional

import httpx

from app.config import get_settings
from app.connectors.base import BaseConnector, RawPost

logger = logging.getLogger(__name__)

AUTH_URL = "https://open.tiktokapis.com/v2/oauth/token/"
RESEARCH_API_URL = "https://open.tiktokapis.com/v2/research/video/query/"
VIDEO_FIELDS = (
    "id,video_description,create_time,username,"
    "like_count,comment_count,share_count,view_count,hashtag_names"
)

# Default search terms when DB keywords are empty / for Research API query shaping
DEFAULT_TIKTOK_KEYWORDS = [
    "Bank Indonesia Bali",
    "BI Bali",
    "KPwBI Bali",
    "QRIS Bali",
    "inflasi Bali",
]
DEFAULT_TIKTOK_HASHTAGS = [
    "bibali",
    "qrisbali",
    "bankindonesia",
    "bankindonesiabali",
    "inflasibali",
    "ekonomibali",
    "umkmbali",
]


class TikTokConnector(BaseConnector):
    id = "tiktok"
    name = "TikTok (Research API)"
    description = (
        "Query video/caption via TikTok Research API (butuh approval research + "
        "Client Key & Secret). Sentimen diproses pipeline platform (LLM/InSet)."
    )
    requires_api_key = True

    def is_configured(self) -> bool:
        s = get_settings()
        return bool(s.tiktok_client_key and s.tiktok_client_secret)

    def get_access_token(self) -> Optional[str]:
        settings = get_settings()
        payload = {
            "client_key": settings.tiktok_client_key,
            "client_secret": settings.tiktok_client_secret,
            "grant_type": "client_credentials",
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(AUTH_URL, data=payload, headers=headers)
        if resp.status_code != 200:
            logger.error("TikTok token error: %s %s", resp.status_code, resp.text[:500])
            raise RuntimeError(f"Gagal mendapatkan TikTok access token: {resp.text[:300]}")
        data = resp.json()
        # Research API may nest under data
        token = data.get("access_token") or (data.get("data") or {}).get("access_token")
        if not token:
            raise RuntimeError(f"Respons token TikTok tidak berisi access_token: {data}")
        return token

    def _build_query(self, keywords: List[str]) -> dict:
        text_keywords: List[str] = []
        hashtags: List[str] = []

        for raw in keywords:
            item = raw.strip()
            if not item:
                continue
            if item.startswith("#") or item.lower().replace(" ", "") in {
                h.lower() for h in DEFAULT_TIKTOK_HASHTAGS
            }:
                hashtags.append(item.lstrip("#").lower().replace(" ", ""))
            else:
                text_keywords.append(item)

        if not text_keywords:
            text_keywords = list(DEFAULT_TIKTOK_KEYWORDS)
        if not hashtags:
            hashtags = list(DEFAULT_TIKTOK_HASHTAGS)

        # Cap OR clauses to keep request size reasonable
        text_keywords = text_keywords[:8]
        hashtags = hashtags[:8]

        or_clauses: List[dict] = []
        for kw in text_keywords:
            or_clauses.append(
                {
                    "operation": "EQ",
                    "field_name": "keyword",
                    "field_values": [kw],
                }
            )
        for tag in hashtags:
            or_clauses.append(
                {
                    "operation": "EQ",
                    "field_name": "hashtag_name",
                    "field_values": [tag],
                }
            )

        return {
            "and": [
                {
                    "operation": "IN",
                    "field_name": "region_code",
                    "field_values": ["ID"],
                },
                {"or": or_clauses},
            ]
        }

    def _match_keyword(self, caption: str, hashtag_names: List[str], keywords: List[str]) -> str:
        hay = f"{caption} {' '.join(hashtag_names)}".lower()
        for kw in keywords:
            needle = kw.lstrip("#").lower()
            if needle and needle in hay:
                return kw if kw.startswith("#") else kw
        if hashtag_names:
            return f"#{hashtag_names[0]}"
        return keywords[0] if keywords else "tiktok"

    def fetch_posts(self, keywords: List[str], limit: int = 50) -> List[RawPost]:
        settings = get_settings()
        if not self.is_configured():
            return []

        token = self.get_access_token()
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=settings.tiktok_lookback_days)
        max_count = min(max(limit, 1), 100)

        search_terms = keywords or (DEFAULT_TIKTOK_KEYWORDS + [f"#{h}" for h in DEFAULT_TIKTOK_HASHTAGS])
        payload = {
            "query": self._build_query(search_terms),
            "start_date": start_date.strftime("%Y%m%d"),
            "end_date": end_date.strftime("%Y%m%d"),
            "max_count": max_count,
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                RESEARCH_API_URL,
                headers=headers,
                params={"fields": VIDEO_FIELDS},
                json=payload,
            )

        if resp.status_code != 200:
            logger.error("TikTok query error: %s %s", resp.status_code, resp.text[:800])
            raise RuntimeError(f"TikTok Research API error: {resp.text[:400]}")

        body = resp.json()
        videos = (body.get("data") or {}).get("videos") or body.get("videos") or []
        posts: List[RawPost] = []

        for vid in videos:
            caption = (vid.get("video_description") or vid.get("caption") or "").strip()
            if not caption:
                caption = "(tanpa caption)"
            username = vid.get("username") or "unknown"
            video_id = str(vid.get("id") or "")
            if not video_id:
                continue

            create_time = vid.get("create_time")
            if isinstance(create_time, (int, float)):
                posted_at = datetime.utcfromtimestamp(int(create_time))
            elif isinstance(create_time, str) and create_time.isdigit():
                posted_at = datetime.utcfromtimestamp(int(create_time))
            else:
                posted_at = datetime.utcnow()

            hashtag_names = vid.get("hashtag_names") or []
            if isinstance(hashtag_names, str):
                hashtag_names = [hashtag_names]

            posts.append(
                RawPost(
                    source="tiktok",
                    source_post_id=video_id,
                    author=username,
                    text_raw=caption[:5000],
                    url=f"https://www.tiktok.com/@{username}/video/{video_id}",
                    posted_at=posted_at,
                    keyword_matched=self._match_keyword(caption, hashtag_names, search_terms),
                )
            )

        return posts

"""News connector wrapping the RSS/Google News scraper (Phase 1 — free & legal)."""

from __future__ import annotations

from typing import List

from app.connectors.base import BaseConnector, RawPost
from app.services.news_scraper import fetch_news_for_keyword


class NewsConnector(BaseConnector):
    id = "news"
    name = "Berita Online (RSS)"
    description = (
        "Google News RSS / feed berita Indonesia berdasarkan keyword. "
        "Tidak memerlukan API key."
    )
    requires_api_key = False

    def is_configured(self) -> bool:
        return True

    def fetch_posts(self, keywords: List[str], limit: int = 50) -> List[RawPost]:
        per_kw = max(1, limit // max(len(keywords), 1))
        results: List[RawPost] = []
        for kw in keywords:
            for item in fetch_news_for_keyword(kw, limit=per_kw):
                results.append(
                    RawPost(
                        source=item["source"],
                        source_post_id=item["source_post_id"],
                        author=item.get("author"),
                        text_raw=item["text_raw"],
                        url=item.get("url"),
                        posted_at=item["posted_at"],
                        keyword_matched=item.get("keyword_matched"),
                    )
                )
        return results[:limit]

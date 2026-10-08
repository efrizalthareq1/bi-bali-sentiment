"""Outlook / Microsoft 365 connector via Microsoft Graph Mail API."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from html import unescape
from typing import List, Optional

import httpx

from app.config import get_settings
from app.connectors.base import BaseConnector, RawPost

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
TOKEN_URL_TMPL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"


def _strip_html(html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_graph_datetime(value: Optional[str]) -> datetime:
    if not value:
        return datetime.utcnow()
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return datetime.utcnow()


class OutlookConnector(BaseConnector):
    id = "outlook"
    name = "Outlook (Microsoft 365)"
    description = (
        "Baca email Inbox via Microsoft Graph (Azure AD app). "
        "Filter keyword terkait BI Bali / QRIS / dll. "
        "Butuh Tenant ID, Client ID, Client Secret, dan mailbox."
    )
    requires_api_key = True

    def is_configured(self) -> bool:
        s = get_settings()
        if s.outlook_access_token:
            return True
        return bool(
            s.outlook_tenant_id
            and s.outlook_client_id
            and s.outlook_client_secret
            and s.outlook_mailbox
        )

    def get_access_token(self) -> str:
        settings = get_settings()
        if settings.outlook_access_token:
            return settings.outlook_access_token

        token_url = TOKEN_URL_TMPL.format(tenant=settings.outlook_tenant_id)
        data = {
            "client_id": settings.outlook_client_id,
            "client_secret": settings.outlook_client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        }
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(token_url, data=data)
        if resp.status_code != 200:
            raise RuntimeError(
                f"Gagal token Outlook/Azure AD: {resp.status_code} {resp.text[:400]}"
            )
        token = resp.json().get("access_token")
        if not token:
            raise RuntimeError("Respons Azure AD tidak berisi access_token")
        return token

    def _mailbox_base(self) -> str:
        settings = get_settings()
        if settings.outlook_access_token and not settings.outlook_mailbox:
            return f"{GRAPH_BASE}/me"
        mailbox = settings.outlook_mailbox.strip()
        if not mailbox:
            raise RuntimeError("OUTLOOK_MAILBOX belum diisi")
        return f"{GRAPH_BASE}/users/{mailbox}"

    def _match_keyword(self, text: str, keywords: List[str]) -> Optional[str]:
        lowered = text.lower()
        for kw in keywords:
            if kw and kw.lstrip("#").lower() in lowered:
                return kw
        return None

    def fetch_posts(self, keywords: List[str], limit: int = 50) -> List[RawPost]:
        if not self.is_configured():
            return []

        settings = get_settings()
        token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "ConsistencyLevel": "eventual",
        }

        text_keywords = [
            k.strip()
            for k in keywords
            if k and not str(k).startswith("#") and not str(k).startswith("ig_")
        ][:10]
        if not text_keywords:
            text_keywords = [
                "Bank Indonesia Bali",
                "BI Bali",
                "KPwBI",
                "QRIS",
                "inflasi Bali",
            ]

        lookback = max(1, settings.outlook_lookback_days)
        # KQL search across subject/body; Graph $search needs ConsistencyLevel
        search_terms = " OR ".join(f'"{kw}"' for kw in text_keywords[:6])
        folder = (settings.outlook_folder or "inbox").strip() or "inbox"
        base = self._mailbox_base()

        params = {
            "$top": min(max(limit, 1), 50),
            "$select": "id,subject,bodyPreview,body,from,receivedDateTime,webLink,isRead",
            "$search": search_terms,
        }

        url = f"{base}/mailFolders/{folder}/messages"
        posts: List[RawPost] = []
        seen: set[str] = set()
        cutoff = datetime.utcnow() - timedelta(days=lookback)
        used_search = True

        with httpx.Client(timeout=60.0) as client:
            resp = client.get(url, headers=headers, params=params)
            if resp.status_code >= 400:
                logger.warning(
                    "Outlook $search failed (%s), fallback list+local filter: %s",
                    resp.status_code,
                    resp.text[:300],
                )
                used_search = False
                params = {
                    "$top": min(max(limit * 3, 30), 100),
                    "$select": "id,subject,bodyPreview,body,from,receivedDateTime,webLink",
                    "$orderby": "receivedDateTime desc",
                }
                resp = client.get(url, headers=headers, params=params)

            if resp.status_code >= 400:
                raise RuntimeError(
                    f"Outlook Graph API error: {resp.status_code} {resp.text[:400]}"
                )

            messages = resp.json().get("value") or []

        for msg in messages:
            if len(posts) >= limit:
                break
            msg_id = str(msg.get("id") or "")
            if not msg_id or msg_id in seen:
                continue

            posted_at = _parse_graph_datetime(msg.get("receivedDateTime"))
            if posted_at < cutoff:
                continue

            subject = (msg.get("subject") or "").strip()
            preview = (msg.get("bodyPreview") or "").strip()
            body_obj = msg.get("body") or {}
            body_content = body_obj.get("content") or ""
            if (body_obj.get("contentType") or "").lower() == "html":
                body_text = _strip_html(body_content)
            else:
                body_text = body_content.strip()

            text_parts = [p for p in (subject, preview, body_text) if p]
            text = "\n\n".join(text_parts)[:5000]
            if not text.strip():
                continue

            matched = self._match_keyword(text, text_keywords)
            if matched is None and used_search:
                matched = text_keywords[0]
            if matched is None:
                continue

            from_obj = ((msg.get("from") or {}).get("emailAddress")) or {}
            author = from_obj.get("address") or from_obj.get("name") or "outlook"

            seen.add(msg_id)
            posts.append(
                RawPost(
                    source="outlook",
                    source_post_id=msg_id[:200],
                    author=author,
                    text_raw=text,
                    url=msg.get("webLink"),
                    posted_at=posted_at,
                    keyword_matched=matched,
                )
            )

        return posts

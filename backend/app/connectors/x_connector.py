"""X/Twitter connector — fokus percakapan netizen tentang BI, bukan akun resmi."""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import List, Optional, Set
from urllib.parse import quote_plus

import feedparser
import httpx

from app.config import get_settings
from app.connectors.base import BaseConnector, RawPost

logger = logging.getLogger(__name__)

# Akun institusi BI — dikecualikan (kita mau suara netizen / publik non-BI)
OFFICIAL_X_ACCOUNTS: Set[str] = {
    "bank_indonesia",
    "bi_provinsibali",
    "bankindonesia",
    "bi_official",
    "biindonesia",
    "bi_jabar",
    "bi_riau",
    "bi_jateng",
    "bi_jatim",
    "bi_sumut",
    "bi_sumsel",
    "bi_sulsel",
    "bi_kalbar",
    "bi_kaltim",
    "bi_diy",
    "bi_dki",
}

RSSHUB_BASES = [
    "https://rsshub.app",
    "https://rsshub.rssforever.com",
]

# Topik isu terkini yang sering dibahas publik soal BI
NETIZEN_TOPIC_QUERIES = [
    '"Bank Indonesia" (inflasi OR "BI-Rate" OR QRIS OR GPIPS OR "suku bunga") (site:x.com OR site:twitter.com)',
    '"BI-Rate" (naik OR turun OR tetap) (site:x.com OR site:twitter.com)',
    '"QRIS" (Bank Indonesia OR BI) (site:x.com OR site:twitter.com)',
    '"QRIS Run" (site:x.com OR site:twitter.com)',
    '"QRIS Summer Run" (site:x.com OR site:twitter.com)',
    'qrissummerrun (site:x.com OR site:twitter.com)',
    '"GPIPS" OR "GPIB" (Bank Indonesia OR BI) (site:x.com OR site:twitter.com)',
    '"Bank Indonesia Bali" OR "BI Bali" OR KPwBI (site:x.com OR site:twitter.com)',
    'rupiah (menguat OR melemah OR "Bank Indonesia") (site:x.com OR site:twitter.com)',
    'inflasi Bali OR "inflasi Indonesia" BI (site:x.com OR site:twitter.com)',
]


class XConnector(BaseConnector):
    id = "x"
    name = "X (Twitter)"
    description = (
        "Percakapan netizen di X tentang Bank Indonesia / isu kebijakan "
        "(bukan postingan akun resmi BI). Isi X_BEARER_TOKEN untuk Recent Search API."
    )
    requires_api_key = False

    def is_configured(self) -> bool:
        return True

    def get_info(self, post_count: int = 0, last_sync=None):
        configured_api = bool(get_settings().x_bearer_token)
        info = super().get_info(post_count=post_count, last_sync=last_sync)
        info.requires_api_key = True
        info.configured = True
        info.status = "connected" if configured_api else "ready"
        info.description = (
            "Mode API: recent search netizen (mengecualikan from:bank_indonesia)."
            if configured_api
            else (
                "Mode publik: mention netizen site:x.com tentang BI / inflasi / QRIS / GPIPS. "
                "Bukan timeline akun resmi BI."
            )
        )
        return info

    def fetch_posts(self, keywords: List[str], limit: int = 50) -> List[RawPost]:
        settings = get_settings()
        if settings.x_bearer_token:
            try:
                api_posts = self._fetch_via_api(keywords, limit)
                api_posts = [p for p in api_posts if not self._is_official_author(p.author)]
                if api_posts:
                    return api_posts[:limit]
            except Exception as exc:
                logger.warning("X API failed, falling back to public sources: %s", exc)

        posts: List[RawPost] = []
        try:
            posts.extend(self._fetch_via_rsshub_search(keywords, limit=limit))
        except Exception as exc:
            logger.warning("X RSSHub search failed: %s", exc)

        remaining = max(0, limit - len(posts))
        if remaining:
            try:
                posts.extend(self._fetch_via_public_rss(keywords, limit=remaining))
            except Exception as exc:
                logger.warning("X public RSS failed: %s", exc)

        # Dedup + buang akun resmi
        seen: set[str] = set()
        clean: List[RawPost] = []
        for p in posts:
            if self._is_official_author(p.author):
                continue
            if p.source_post_id in seen:
                continue
            if p.source_post_id.startswith("profile-"):
                continue
            # Hindari URL yang masih Google wrapper tanpa sinyal X yang jelas
            if "news.google.com" in (p.url or "") and not re.search(
                r"(bank indonesia|bi-rate|qris|gpips|inflasi|rupiah)",
                (p.text_raw or "").lower(),
            ):
                continue
            seen.add(p.source_post_id)
            clean.append(p)
        return clean[:limit]

    def _is_official_author(self, author: Optional[str]) -> bool:
        if not author:
            return False
        a = author.lower().lstrip("@").strip()
        if a in OFFICIAL_X_ACCOUNTS:
            return True
        # KPwBI / kantor wilayah BI di X biasanya bi_xxx
        if a.startswith("bi_") or a.startswith("bank_indonesia"):
            return True
        if a in {"bankindonesia", "biindonesia"}:
            return True
        return False

    def _fetch_via_api(self, keywords: List[str], limit: int = 50) -> List[RawPost]:
        settings = get_settings()
        phrases = []
        for kw in keywords[:8]:
            kw = kw.strip()
            if not kw:
                continue
            if kw.startswith("#"):
                phrases.append(kw)
            else:
                phrases.append(f'"{kw}"')
        if not phrases:
            phrases = ['"Bank Indonesia"', '"BI-Rate"', "QRIS", "GPIPS", "inflasi"]

        # Netizen only: exclude official BI accounts
        query = (
            "("
            + " OR ".join(phrases[:6])
            + ') ("Bank Indonesia" OR BI-Rate OR QRIS OR GPIPS OR inflasi) '
            "lang:id -is:retweet -from:bank_indonesia -from:BI_ProvinsiBali"
        )
        headers = {"Authorization": f"Bearer {settings.x_bearer_token}"}
        params = {
            "query": query,
            "max_results": min(max(limit, 10), 100),
            "tweet.fields": "created_at,author_id,text,lang",
            "expansions": "author_id",
            "user.fields": "username,name",
        }

        with httpx.Client(timeout=45.0) as client:
            resp = client.get(
                "https://api.twitter.com/2/tweets/search/recent",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

        users = {
            u["id"]: u.get("username")
            for u in data.get("includes", {}).get("users", [])
        }
        posts: List[RawPost] = []
        for tw in data.get("data", []):
            created = tw.get("created_at")
            posted_at = (
                datetime.fromisoformat(created.replace("Z", "+00:00")).replace(tzinfo=None)
                if created
                else datetime.utcnow()
            )
            text = tw.get("text") or ""
            matched = next(
                (k for k in keywords if k.lstrip("#").lower() in text.lower()),
                keywords[0] if keywords else "Bank Indonesia",
            )
            username = users.get(tw.get("author_id"), tw.get("author_id"))
            if self._is_official_author(username):
                continue
            posts.append(
                RawPost(
                    source="x",
                    source_post_id=tw["id"],
                    author=username,
                    text_raw=text,
                    url=f"https://x.com/{username}/status/{tw['id']}",
                    posted_at=posted_at,
                    keyword_matched=matched,
                )
            )
        return posts

    def _fetch_via_rsshub_search(self, keywords: List[str], limit: int) -> List[RawPost]:
        """Cari tweet publik via RSSHub search (bukan timeline akun resmi)."""
        keys = [k for k in keywords if k and not k.startswith("#")][:5] or [
            "Bank Indonesia",
            "BI-Rate",
            "QRIS",
            "GPIPS",
            "inflasi BI",
        ]
        search_terms = list(keys)
        for extra in ("Bank Indonesia inflasi", "QRIS Summer Run", "QRIS Run", "qrissummerrun", "BI Bali", "GPIPS"):
            if extra not in search_terms:
                search_terms.append(extra)
        search_terms = search_terms[:8]

        posts: List[RawPost] = []
        seen: set[str] = set()
        for term in search_terms:
            if len(posts) >= limit:
                break
            for base in RSSHUB_BASES:
                if len(posts) >= limit:
                    break
                for path in (
                    f"/twitter/search/{quote_plus(term)}",
                    f"/twitter/keyword/{quote_plus(term)}",
                ):
                    url = f"{base}{path}"
                    try:
                        with httpx.Client(timeout=12.0, follow_redirects=True) as client:
                            resp = client.get(url)
                            if resp.status_code >= 400 or not resp.text.strip():
                                continue
                            feed = feedparser.parse(resp.text)
                    except Exception as exc:
                        logger.debug("RSSHub X search %s failed: %s", url, exc)
                        continue
                    if not feed.entries:
                        continue

                    for entry in feed.entries:
                        if len(posts) >= limit:
                            break
                        title = getattr(entry, "title", "") or ""
                        summary = getattr(entry, "summary", "") or ""
                        link = getattr(entry, "link", "") or ""
                        clean = re.sub(r"<[^>]+>", " ", summary)
                        clean = re.sub(r"\s+", " ", clean).strip()
                        text = title if not clean or clean in title else f"{title}\n{clean}"

                        author = None
                        status_id = None
                        m = re.search(
                            r"(?:x|twitter)\.com/([^/\s\"'<>]+)/status/(\d+)",
                            f"{link}\n{text}",
                            re.I,
                        )
                        if m:
                            author = m.group(1)
                            status_id = m.group(2)
                            link = f"https://x.com/{author}/status/{status_id}"
                        if not status_id:
                            continue
                        if self._is_official_author(author):
                            continue
                        if status_id in seen:
                            continue
                        seen.add(status_id)

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

                        posts.append(
                            RawPost(
                                source="x",
                                source_post_id=status_id,
                                author=author,
                                text_raw=text[:5000],
                                url=link,
                                posted_at=posted_at,
                                keyword_matched=term,
                            )
                        )
                    if posts:
                        break  # satu mirror RSSHub cukup per term
        return posts

    def _fetch_via_public_rss(self, keywords: List[str], limit: int = 50) -> List[RawPost]:
        """Indeks publik (Google News) untuk percakapan di X tentang BI — fokus netizen."""
        from app.services.url_resolve import resolve_article_url

        text_keywords = [
            k for k in keywords if k and not k.startswith("#") and not k.startswith("ig_")
        ][:8] or [
            "Bank Indonesia",
            "BI Bali",
            "GPIPS",
            "inflasi",
            "QRIS Run",
            "QRIS",
            "BI-Rate",
        ]

        queries = list(NETIZEN_TOPIC_QUERIES)
        for kw in text_keywords[:6]:
            queries.append(f'"{kw}" (site:x.com OR site:twitter.com)')

        posts: List[RawPost] = []
        seen: set[str] = set()
        resolve_budget = 25  # batasi decode lambat

        for q in queries:
            if len(posts) >= limit:
                break
            url = (
                "https://news.google.com/rss/search?"
                f"q={quote_plus(q)}&hl=id&gl=ID&ceid=ID:id"
            )
            try:
                feed = feedparser.parse(url)
            except Exception as exc:
                logger.warning("X public RSS failed for %s: %s", q, exc)
                continue

            for entry in feed.entries:
                if len(posts) >= limit:
                    break
                title = getattr(entry, "title", "") or ""
                summary = getattr(entry, "summary", "") or ""
                link = getattr(entry, "link", "") or ""
                blob = f"{title}\n{summary}\n{link}"
                # Hanya item yang jelas dari ekosistem X
                if not re.search(r"(?:x\.com|twitter\.com|\bx\b)", blob, re.I):
                    if " - x.com" not in title.lower() and "/ x" not in title.lower():
                        continue

                clean_summary = re.sub(r"<[^>]+>", " ", summary)
                clean_summary = clean_summary.replace("&nbsp;", " ").replace("&amp;", "&")
                clean_summary = re.sub(r"\s+", " ", clean_summary).strip()
                text = title
                if clean_summary and clean_summary not in title:
                    text = f"{title}. {clean_summary}"
                if not text.strip():
                    continue

                author = None
                handle_m = re.search(r"\(@([A-Za-z0-9_]{2,30})\)", title)
                if handle_m:
                    author = handle_m.group(1)
                if self._is_official_author(author):
                    continue
                # Skip judul yang jelas dari akun resmi BI / kampanye resmi
                if re.search(
                    r"@bank_indonesia\b|@BI_ProvinsiBali\b|#SobatRupiah|Bank Indonesia Channel",
                    title,
                    re.I,
                ):
                    continue
                if re.search(r"halo\s+#sobatrupiah", text, re.I):
                    continue

                resolved = None
                status_m = re.search(
                    r"https?://(?:www\.)?(?:x|twitter)\.com/([^/\s\"'<>]+)/status/(\d+)",
                    blob,
                    re.I,
                )
                if status_m:
                    author = author or status_m.group(1)
                    if not self._is_official_author(author):
                        resolved = f"https://x.com/{author}/status/{status_m.group(2)}"

                if not resolved and resolve_budget > 0 and link:
                    resolve_budget -= 1
                    try:
                        candidate = resolve_article_url(link, fast=False) or ""
                    except Exception:
                        candidate = ""
                    sm = re.search(
                        r"(?:x|twitter)\.com/([^/\s\"'<>]+)/status/(\d+)",
                        candidate,
                        re.I,
                    )
                    if sm and not self._is_official_author(sm.group(1)):
                        author = author or sm.group(1)
                        resolved = f"https://x.com/{author}/status/{sm.group(2)}"
                    elif re.search(r"(?:x|twitter)\.com/([^/\s\"'<>]+)/?", candidate, re.I):
                        um = re.search(r"(?:x|twitter)\.com/([^/\s\"'<>]+)", candidate, re.I)
                        if um and um.group(1) not in {"i", "intent", "share", "search", "home"}:
                            author = author or um.group(1)
                            if self._is_official_author(author):
                                continue
                            resolved = f"https://x.com/{author}"

                if not resolved:
                    # Fallback: simpan sinyal percakapan X dari indeks (bukan akun resmi)
                    if not author:
                        # coba ambil nama sebelum " / Posts / X"
                        name_m = re.match(r"^(.+?)\s*/\s*Posts\s*/\s*X", title, re.I)
                        if name_m:
                            author = name_m.group(1).strip()[:80]
                    if self._is_official_author(author):
                        continue
                    if author:
                        resolved = f"https://x.com/{author}"
                    else:
                        # tetap pakai link Google News agar bisa dibuka
                        resolved = link
                        author = author or "netizen_x"

                status_id = None
                m = re.search(r"/status/(\d+)", resolved)
                if m:
                    status_id = m.group(1)

                source_id = status_id or hashlib.sha256(
                    f"{resolved}|{title}".encode("utf-8")
                ).hexdigest()[:32]
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

                matched = next(
                    (k for k in text_keywords if k.lower() in text.lower()),
                    text_keywords[0],
                )
                posts.append(
                    RawPost(
                        source="x",
                        source_post_id=source_id,
                        author=author or "netizen",
                        text_raw=text[:5000],
                        url=resolved,
                        posted_at=posted_at,
                        keyword_matched=matched,
                    )
                )

        return posts[:limit]

    def _extract_x_author(self, url: str, entry) -> Optional[str]:
        m = re.search(r"(?:x|twitter)\.com/([^/]+)/status/", url or "")
        if m and m.group(1) not in {"i", "intent", "share", "search"}:
            return m.group(1)
        src = getattr(entry, "source", None)
        if isinstance(src, dict) and src.get("title"):
            return src.get("title")
        return getattr(entry, "author", None)

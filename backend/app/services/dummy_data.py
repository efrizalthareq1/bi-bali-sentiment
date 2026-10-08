"""Synthetic post generator for dashboard testing before real data arrives."""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.constants import DEFAULT_KEYWORDS
from app.instagram_hashtags import (
    INSTAGRAM_PRIORITY_HASHTAGS,
    all_formatted_hashtags,
    format_hashtag,
)
from app.models import Keyword, Post, SentimentScore
from app.services.lexicon import analyze_with_lexicon

SOURCES = ["x", "instagram", "tiktok", "news", "manual"]

TEMPLATES_POSITIF = [
    "Program {keyword} benar-benar membantu UMKM lokal di Aceh. Apresiasi untuk KPwBI Aceh!",
    "Penukaran uang di {keyword} lancar sekali, petugasnya ramah dan profesional.",
    "QRIS Aceh memudahkan transaksi di pasar tradisional. Inovasi BI Aceh patut diacungi jempol.",
    "Inflasi Aceh terkendali berkat koordinasi {keyword} dengan Pemda. Kerja bagus!",
    "Ekonomi syariah Aceh semakin maju. Semangat {keyword}!",
    "Sistem pembayaran di Banda Aceh semakin modern. Terima kasih Bank Indonesia Aceh.",
    "UMKM Aceh naik kelas berkat dukungan digitalisasi. Luar biasa!",
    "Program Meuseuraya memberi dampak positif bagi pelaku usaha lokal.",
    "Keuangan syariah Aceh terbantu akses literasi dari BI. Mantap!",
    "Digitalisasi Aceh berjalan baik, kepercayaan pasar terhadap {keyword} meningkat.",
]

TEMPLATES_NEGATIF = [
    "Antrian penukaran uang di Banda Aceh terlalu lama, pelayanan {keyword} perlu diperbaiki.",
    "Sosialisasi QRIS Aceh masih kurang merata di desa. Banyak pedagang masih bingung.",
    "Inflasi Aceh terasa memberatkan harga kebutuhan pokok. Harap {keyword} lebih responsif.",
    "Informasi TPID Aceh tidak jelas di situs resmi. Frustrasi mencari update terbaru.",
    "Program {keyword} terkesan elitis, UMKM kecil belum merasakan manfaatnya.",
    "Kendala teknis sistem pembayaran mengganggu transaksi harian di Aceh.",
    "Ekonomi Aceh masih lesu, stimulus dari BI dinilai belum cukup.",
    "Komplain soal uang rusak ditolak di beberapa titik penukaran. Kecewa dengan layanan.",
    "Banyak pelaku usaha mengeluhkan proses {keyword} yang ribet dan lambat.",
    "Transparansi data inflasi Aceh kurang, publik kesulitan memahami kebijakan.",
]

TEMPLATES_NETRAL = [
    "Bank Indonesia Aceh mengumumkan jadwal penukaran uang menjelang Hari Raya.",
    "KPwBI Aceh menggelar sosialisasi {keyword} di Banda Aceh minggu ini.",
    "Data inflasi Aceh bulan ini akan dirilis sesuai kalender resmi BI.",
    "QRIS Aceh terus diperluas ke merchant baru menurut laporan {keyword}.",
    "Monitoring TP2DD Aceh dilakukan secara berkala oleh Kantor Perwakilan BI.",
    "UMKM Aceh mengikuti workshop digitalisasi sistem pembayaran.",
    "Laporan ekonomi Aceh dibahas dalam rapat koordinasi {keyword}.",
    "Program ETPD Aceh masuk agenda literasi keuangan daerah.",
    "Diskusi keuangan syariah Aceh digelar bersama komunitas lokal.",
    "Update CBPR dan Cinta Bangga Paham Rupiah disampaikan ke publik.",
]

IG_CAPTION_TEMPLATES = [
    "{body}\n\n{tags}",
    "{body}\n.\n.\n{tags}",
    "Update dari Aceh\n{body}\n\n{tags}",
]

AUTHORS = [
    "warga_bandaaceh", "umkm_aceh", "media_aceh", "pedagang_pasar",
    "mahasiswa_unsyiah", "fintech_id", "reporter_bisnis", "komunitas_qris",
    "investor_aceh", "netizen_lhokseumawe", "komunitas_halal", "pariwisata_aceh",
]


def seed_keywords(db: Session) -> int:
    """Seed Aceh keywords/hashtags and deactivate obsolete Bali-focused entries."""
    allowed = {k for k, _ in DEFAULT_KEYWORDS} | {h for h, _ in all_formatted_hashtags()}
    created = 0

    for row in db.query(Keyword).all():
        if row.keyword not in allowed:
            # Drop legacy Bali / Summer Run focus from active monitoring
            if (
                "bali" in row.keyword.lower()
                or "summer" in row.keyword.lower()
                or "baligivation" in row.keyword.lower()
                or "denpasar" in row.keyword.lower()
                or (row.category.startswith("ig_") and row.keyword not in allowed)
            ):
                row.active = False

    for keyword, category in DEFAULT_KEYWORDS:
        exists = db.query(Keyword).filter(Keyword.keyword == keyword).first()
        if exists:
            exists.category = category
            exists.active = True
            continue
        db.add(Keyword(keyword=keyword, category=category, active=True))
        created += 1
    for hashtag, category in all_formatted_hashtags():
        exists = db.query(Keyword).filter(Keyword.keyword == hashtag).first()
        if exists:
            exists.category = category
            exists.active = True
            continue
        db.add(Keyword(keyword=hashtag, category=category, active=True))
        created += 1
    db.commit()
    return created


def _analyze_and_save(db: Session, post: Post, text: str, forced: str | None = None) -> None:
    sentiment, confidence, topic, reasoning = analyze_with_lexicon(text)
    if forced and random.random() < 0.75:
        sentiment = forced
        confidence = round(random.uniform(0.7, 0.95), 3)
    db.add(
        SentimentScore(
            post_id=post.id,
            sentiment=sentiment,
            confidence=confidence,
            topic_tag=topic,
            reasoning=reasoning,
            model_used="inset-lexicon",
        )
    )
    db.commit()


def generate_dummy_posts(db: Session, count: int = 180, analyze: bool = True) -> tuple[int, int]:
    """Create synthetic posts. Returns (posts_created, analyzed_count)."""
    seed_keywords(db)
    keywords = [k for k, _ in DEFAULT_KEYWORDS]
    created = 0
    analyzed = 0
    now = datetime.utcnow()

    for i in range(count):
        roll = random.random()
        if roll < 0.40:
            templates = TEMPLATES_POSITIF
            forced = "positif"
        elif roll < 0.65:
            templates = TEMPLATES_NEGATIF
            forced = "negatif"
        else:
            templates = TEMPLATES_NETRAL
            forced = "netral"

        keyword = random.choice(keywords)
        text = random.choice(templates).format(keyword=keyword)
        source = random.choice(SOURCES)
        days_ago = random.randint(0, 90)
        hours_ago = random.randint(0, 23)
        posted_at = now - timedelta(days=days_ago, hours=hours_ago)

        matched = keyword
        if source == "instagram":
            tag = format_hashtag(random.choice(INSTAGRAM_PRIORITY_HASHTAGS))
            extra = " ".join(
                format_hashtag(t)
                for t in random.sample(
                    INSTAGRAM_PRIORITY_HASHTAGS, k=min(3, len(INSTAGRAM_PRIORITY_HASHTAGS))
                )
            )
            text = random.choice(IG_CAPTION_TEMPLATES).format(body=text, tags=extra)
            matched = tag

        post = Post(
            source=source,
            source_post_id=f"dummy-{i}-{random.randint(1000, 9999)}",
            author=random.choice(AUTHORS),
            text_raw=text,
            url=f"https://example.com/{source}/post/{i}",
            posted_at=posted_at,
            keyword_matched=matched,
        )
        db.add(post)
        try:
            db.commit()
            db.refresh(post)
            created += 1
        except IntegrityError:
            db.rollback()
            continue

        if analyze:
            _analyze_and_save(db, post, text, forced)
            analyzed += 1

    return created, analyzed


def generate_instagram_hashtag_demo(
    db: Session,
    per_hashtag: int = 3,
    analyze: bool = True,
    hashtags: list[str] | None = None,
) -> tuple[int, int]:
    """
    Generate synthetic Instagram posts for catalog hashtags.
    Useful for dashboard testing before Graph API credentials are available.
    """
    seed_keywords(db)
    tags = hashtags or [format_hashtag(t) for t in INSTAGRAM_PRIORITY_HASHTAGS]
    created = 0
    analyzed = 0
    now = datetime.utcnow()

    for tag in tags:
        for j in range(per_hashtag):
            roll = random.random()
            if roll < 0.45:
                body = random.choice(TEMPLATES_POSITIF).format(keyword=tag)
                forced = "positif"
            elif roll < 0.7:
                body = random.choice(TEMPLATES_NEGATIF).format(keyword=tag)
                forced = "negatif"
            else:
                body = random.choice(TEMPLATES_NETRAL).format(keyword=tag)
                forced = "netral"

            related = random.sample(
                INSTAGRAM_PRIORITY_HASHTAGS,
                k=min(4, len(INSTAGRAM_PRIORITY_HASHTAGS)),
            )
            tag_line = " ".join(format_hashtag(t) for t in related)
            if tag not in tag_line:
                tag_line = f"{tag} {tag_line}"
            text = random.choice(IG_CAPTION_TEMPLATES).format(body=body, tags=tag_line)
            posted_at = now - timedelta(
                days=random.randint(0, 60), hours=random.randint(0, 23)
            )

            post = Post(
                source="instagram",
                source_post_id=f"ig-demo-{tag.lstrip('#')}-{j}-{random.randint(10000, 99999)}",
                author=random.choice(AUTHORS),
                text_raw=text,
                url=f"https://www.instagram.com/p/demo-{tag.lstrip('#')}-{j}/",
                posted_at=posted_at,
                keyword_matched=tag,
            )
            db.add(post)
            try:
                db.commit()
                db.refresh(post)
                created += 1
            except IntegrityError:
                db.rollback()
                continue

            if analyze:
                _analyze_and_save(db, post, text, forced)
                analyzed += 1

    return created, analyzed


def generate_tiktok_demo(
    db: Session,
    count: int = 60,
    analyze: bool = True,
) -> tuple[int, int]:
    """Synthetic TikTok captions for BI Aceh topics (no API key)."""
    seed_keywords(db)
    tags = [format_hashtag(t) for t in INSTAGRAM_PRIORITY_HASHTAGS[:15]]
    created = 0
    analyzed = 0
    now = datetime.utcnow()

    for i in range(count):
        tag = random.choice(tags)
        roll = random.random()
        if roll < 0.45:
            body = random.choice(TEMPLATES_POSITIF).format(keyword=tag)
            forced = "positif"
        elif roll < 0.7:
            body = random.choice(TEMPLATES_NEGATIF).format(keyword=tag)
            forced = "negatif"
        else:
            body = random.choice(TEMPLATES_NETRAL).format(keyword=tag)
            forced = "netral"

        text = (
            f"{body}\n\n"
            f"{tag} #BIAceh #BankIndonesiaAceh #QRISAceh #EkonomiAceh "
            f"#FYP #Foryou #Aceh #BandaAceh"
        )
        posted_at = now - timedelta(
            days=random.randint(0, 45), hours=random.randint(0, 23)
        )
        author = random.choice(AUTHORS)
        vid = random.randint(1000000000, 9999999999)

        post = Post(
            source="tiktok",
            source_post_id=f"tt-demo-{vid}-{i}",
            author=author,
            text_raw=text,
            url=f"https://www.tiktok.com/@{author}/video/{vid}",
            posted_at=posted_at,
            keyword_matched=tag,
        )
        db.add(post)
        try:
            db.commit()
            db.refresh(post)
            created += 1
        except IntegrityError:
            db.rollback()
            continue

        if analyze:
            _analyze_and_save(db, post, text, forced)
            analyzed += 1

    return created, analyzed


def generate_outlook_demo(
    db: Session,
    count: int = 40,
    analyze: bool = True,
) -> tuple[int, int]:
    """Synthetic Outlook emails for BI Aceh monitoring (no Azure credentials)."""
    seed_keywords(db)
    subjects = [
        "Update inflasi Aceh — ringkasan koordinasi TPID",
        "Undangan sosialisasi QRIS Aceh untuk UMKM",
        "Laporan media: sentimen publik terhadap BI Aceh",
        "Newsletter Bank Indonesia Aceh edisi terbaru",
        "Penukaran uang rupiah di Banda Aceh — jadwal layanan",
        "Clipping berita ekonomi Aceh",
        "Feedback merchant terkait sistem pembayaran QRIS Aceh",
        "Rekap mention media sosial KPwBI Aceh minggu ini",
    ]
    senders = [
        "media.monitor@example.com",
        "umkm.aceh@example.com",
        "newsletter@bankindonesia.go.id",
        "tpid.aceh@example.go.id",
        "clipping@example.com",
    ]
    created = 0
    analyzed = 0
    now = datetime.utcnow()
    keywords = [k for k, _ in DEFAULT_KEYWORDS]

    for i in range(count):
        kw = random.choice(keywords)
        roll = random.random()
        if roll < 0.4:
            body = random.choice(TEMPLATES_POSITIF).format(keyword=kw)
            forced = "positif"
        elif roll < 0.65:
            body = random.choice(TEMPLATES_NEGATIF).format(keyword=kw)
            forced = "negatif"
        else:
            body = random.choice(TEMPLATES_NETRAL).format(keyword=kw)
            forced = "netral"

        subject = random.choice(subjects)
        text = f"Subject: {subject}\n\n{body}\n\nKeyword: {kw}"
        posted_at = now - timedelta(
            days=random.randint(0, 30), hours=random.randint(0, 23)
        )
        sender = random.choice(senders)
        msg_id = f"outlook-demo-{i}-{random.randint(10000, 99999)}"

        post = Post(
            source="outlook",
            source_post_id=msg_id,
            author=sender,
            text_raw=text,
            url=f"https://outlook.office.com/mail/deeplink/demo/{msg_id}",
            posted_at=posted_at,
            keyword_matched=kw,
        )
        db.add(post)
        try:
            db.commit()
            db.refresh(post)
            created += 1
        except IntegrityError:
            db.rollback()
            continue

        if analyze:
            _analyze_and_save(db, post, text, forced)
            analyzed += 1

    return created, analyzed

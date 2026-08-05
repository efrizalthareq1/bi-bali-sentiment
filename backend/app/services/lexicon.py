"""Indonesian lexicon-based sentiment fallback (InSet-inspired word lists)."""

from __future__ import annotations

import re
from typing import Dict, Tuple

# Compact InSet-style polarity lexicon (subset for offline use).
# Scores roughly mirror InSet range (-5 .. +5).
POSITIVE_WORDS: Dict[str, float] = {
    "baik": 3, "bagus": 3, "hebat": 4, "mantap": 4, "sukses": 4,
    "berhasil": 4, "positif": 3, "mendukung": 3, "dukung": 3,
    "apresiasi": 4, "puji": 3, "senang": 3, "gembira": 3, "puas": 3,
    "membantu": 3, "manfaat": 3, "bermanfaat": 4, "efektif": 3,
    "efisien": 3, "lancar": 3, "mudah": 2, "praktis": 3, "aman": 3,
    "stabil": 3, "tumbuh": 3, "naik": 2, "meningkat": 3, "maju": 3,
    "inovasi": 3, "solusi": 3, "terbaik": 4, "unggul": 4, "cerdas": 3,
    "transparan": 3, "akuntabel": 3, "responsif": 3, "cepat": 2,
    "ramah": 3, "profesional": 3, "optimal": 3, "maksimal": 3,
    "sejahtera": 4, "makmur": 4, "pulih": 3, "recovery": 3,
    "dorong": 2, "dorongan": 2, "stimulus": 2, "fasilitasi": 3,
    "kolaborasi": 3, "sinergi": 3, "berprestasi": 4, "apresiatif": 3,
    "bagus sekali": 5, "sangat baik": 5, "luar biasa": 5,
    "terima kasih": 3, "semangat": 3, "berkah": 3, "amanah": 3,
    "keren": 3, "inovatif": 4, "setuju": 2,
}

NEGATIVE_WORDS: Dict[str, float] = {
    "buruk": -3, "jelek": -3, "gagal": -4, "gagal total": -5,
    "negatif": -3, "kecewa": -4, "marah": -4, "kesal": -3,
    "komplain": -3, "keluhan": -3, "masalah": -2, "problematik": -3,
    "sulit": -2, "ribet": -3, "rumit": -2, "lambat": -3, "lama": -2,
    "mahal": -2, "rugi": -3, "merosot": -4, "turun": -2, "anjlok": -4,
    "inflasi tinggi": -4, "krisis": -5, "resesi": -5, "korupsi": -5,
    "tidak transparan": -4, "tidak jelas": -3, "bingung": -2,
    "frustrasi": -4, "kecewa berat": -5, "salah": -2, "keliru": -2,
    "tidak efektif": -4, "tidak membantu": -4, "sia-sia": -3,
    "hambatan": -3, "kendala": -2, "gangguan": -3, "error": -3,
    "gagal bayar": -5, "penipuan": -5, "scam": -5, "palsu": -4,
    "merugikan": -4, "beban": -2, "memberatkan": -3, "semrawut": -4,
    "chaos": -4, "kacau": -4, "parah": -4, "buruk sekali": -5,
    "susah": -2, "potongan": -2, "kejahatan": -5, "ancaman": -4, "rusak": -3,
}

TOPIC_KEYWORDS: Dict[str, list[str]] = {
    "inflasi": ["inflasi", "harga", "ihk", "tekanan harga"],
    "QRIS": ["qris", "qr code", "pembayaran digital", "cashless"],
    "UMKM": ["umkm", "usaha mikro", "pengusaha kecil", "ekspor umkm"],
    "penukaran uang": ["penukaran", "tukar uang", "uang rusak", "kupva", "rupiah"],
    "kurs": ["kurs", "nilai tukar", "dollar", "valas"],
    "pariwisata": ["pariwisata", "wisata", "tourism", "kunjungan"],
    "program BI": ["serambi", "baligivation", "panca kerti", "investment challenge"],
    "sistem pembayaran": ["sistem pembayaran", "payment", "transfer", "kliring"],
}


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^\w\s\-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def detect_topic(text: str) -> str:
    lowered = text.lower()
    for topic, keys in TOPIC_KEYWORDS.items():
        if any(k in lowered for k in keys):
            return topic
    return "umum"


def analyze_with_lexicon(text: str) -> Tuple[str, float, str, str]:
    """Return sentiment, confidence, topic_tag, reasoning using lexicon scores."""
    normalized = _normalize(text)
    score = 0.0
    hits = 0

    # Multi-word phrases first
    phrases = sorted(
        list(POSITIVE_WORDS.items()) + list(NEGATIVE_WORDS.items()),
        key=lambda x: len(x[0]),
        reverse=True,
    )
    remaining = normalized
    for phrase, weight in phrases:
        if " " in phrase and phrase in remaining:
            score += weight
            hits += 1
            remaining = remaining.replace(phrase, " ")

    tokens = remaining.split()
    for token in tokens:
        if token in POSITIVE_WORDS:
            score += POSITIVE_WORDS[token]
            hits += 1
        elif token in NEGATIVE_WORDS:
            score += NEGATIVE_WORDS[token]
            hits += 1

    if hits == 0 or abs(score) < 0.5:
        sentiment = "netral"
        confidence = 0.55 if hits == 0 else min(0.7, 0.5 + abs(score) * 0.05)
    elif score > 0:
        sentiment = "positif"
        confidence = min(0.92, 0.55 + abs(score) * 0.06)
    else:
        sentiment = "negatif"
        confidence = min(0.92, 0.55 + abs(score) * 0.06)

    topic = detect_topic(text)
    reasoning = (
        f"Analisis leksikon InSet: skor {score:.1f} dari {hits} kata polaritas."
    )
    return sentiment, round(confidence, 3), topic, reasoning

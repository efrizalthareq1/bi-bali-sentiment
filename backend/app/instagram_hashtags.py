"""Instagram/social hashtag catalog for KPwBI Aceh monitoring."""

from __future__ import annotations

from typing import List, Tuple

# (hashtag_without_hash, category)
# Stored in DB as "#Hashtag" for clarity in filters/UI.

INSTAGRAM_HASHTAGS: List[Tuple[str, str]] = [
    # Branding & wilayah
    ("BankIndonesiaAceh", "ig_branding"),
    ("BIAceh", "ig_branding"),
    ("BIBandaAceh", "ig_branding"),
    ("KPwBIAceh", "ig_branding"),
    ("BankIndonesia", "ig_branding"),
    ("Aceh", "ig_wilayah"),
    ("BandaAceh", "ig_wilayah"),
    ("CintaBanggaPahamRupiah", "ig_branding"),
    ("CBPR", "ig_branding"),
    ("Rupiah", "ig_branding"),
    ("BanggaBuatanIndonesia", "ig_branding"),
    # Ekonomi & kebijakan daerah
    ("InflasiAceh", "ig_ekonomi"),
    ("TPIDAceh", "ig_ekonomi"),
    ("EkonomiAceh", "ig_ekonomi"),
    ("SistemPembayaran", "ig_ekonomi"),
    ("EkonomiSyariahAceh", "ig_ekonomi"),
    ("KeuanganSyariahAceh", "ig_ekonomi"),
    ("HalalAceh", "ig_ekonomi"),
    # Digitalisasi & pembayaran
    ("QRISAceh", "ig_qris"),
    ("QRISBandaAceh", "ig_qris"),
    ("QRIS", "ig_qris"),
    ("BIFAST", "ig_qris"),
    ("DigitalisasiAceh", "ig_qris"),
    # UMKM & kreatif
    ("UMKMAceh", "ig_umkm"),
    ("UMKMNaikKelas", "ig_umkm"),
    ("UMKMGoDigital", "ig_umkm"),
    ("EkonomiKreatifAceh", "ig_umkm"),
    # Program & pariwisata
    ("PariwisataAceh", "ig_program"),
    ("Meuseuraya", "ig_program"),
    ("TP2DDAceh", "ig_program"),
    ("ETPDAceh", "ig_program"),
]

# Priority for API/public sync (rate limits / capped fetches).
INSTAGRAM_PRIORITY_HASHTAGS: List[str] = [
    "BankIndonesiaAceh",
    "BIAceh",
    "BIBandaAceh",
    "KPwBIAceh",
    "QRISAceh",
    "QRISBandaAceh",
    "InflasiAceh",
    "TPIDAceh",
    "EkonomiAceh",
    "UMKMAceh",
    "EkonomiSyariahAceh",
    "KeuanganSyariahAceh",
    "HalalAceh",
    "DigitalisasiAceh",
    "BandaAceh",
    "Aceh",
    "Meuseuraya",
    "TP2DDAceh",
    "ETPDAceh",
    "PariwisataAceh",
    "EkonomiKreatifAceh",
    "UMKMNaikKelas",
    "UMKMGoDigital",
    "SistemPembayaran",
    "BIFAST",
    "CintaBanggaPahamRupiah",
    "CBPR",
    "Rupiah",
    "BanggaBuatanIndonesia",
]

HASHTAG_CATEGORY_LABELS = {
    "ig_branding": "Branding Bank Indonesia Aceh",
    "ig_wilayah": "Wilayah Aceh",
    "ig_ekonomi": "Ekonomi & Kebijakan Daerah",
    "ig_qris": "Digitalisasi & QRIS",
    "ig_umkm": "UMKM & Ekonomi Kreatif",
    "ig_program": "Program & Pariwisata",
}


def format_hashtag(tag: str) -> str:
    tag = tag.strip().lstrip("#")
    return f"#{tag}"


def all_formatted_hashtags() -> List[Tuple[str, str]]:
    return [(format_hashtag(tag), category) for tag, category in INSTAGRAM_HASHTAGS]


def priority_formatted_hashtags(limit: int | None = None) -> List[str]:
    tags = [format_hashtag(t) for t in INSTAGRAM_PRIORITY_HASHTAGS]
    if limit is not None:
        return tags[:limit]
    return tags

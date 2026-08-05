"""Instagram hashtag catalog for KPwBI Bali monitoring."""

from __future__ import annotations

from typing import List, Tuple

# (hashtag_without_hash, category)
# Stored in DB as "#Hashtag" for clarity in filters/UI.

INSTAGRAM_HASHTAGS: List[Tuple[str, str]] = [
    # 1. Branding Bank Indonesia
    ("BankIndonesia", "ig_branding"),
    ("BIBali", "ig_branding"),
    ("KantorPerwakilanBIBali", "ig_branding"),
    ("BankSentral", "ig_branding"),
    ("BankIndonesiaBali", "ig_branding"),
    ("CintaBanggaPahamRupiah", "ig_branding"),
    ("CBPR", "ig_branding"),
    ("Rupiah", "ig_branding"),
    ("UangRupiah", "ig_branding"),
    ("BanggaBuatanIndonesia", "ig_branding"),
    ("GerakanNasionalBanggaBuatanIndonesia", "ig_branding"),
    ("GernasBBI", "ig_branding"),
    ("BIWadahEdukasi", "ig_branding"),
    ("BelajarEkonomi", "ig_branding"),
    # 2. Ekonomi & Kebijakan Daerah
    ("EkonomiBali", "ig_ekonomi"),
    ("PertumbuhanEkonomiBali", "ig_ekonomi"),
    ("InflasiBali", "ig_ekonomi"),
    ("PengendalianInflasi", "ig_ekonomi"),
    ("TPIDBali", "ig_ekonomi"),
    ("TimPengendalianInflasiDaerah", "ig_ekonomi"),
    ("EkonomiDaerah", "ig_ekonomi"),
    ("StabilitasEkonomi", "ig_ekonomi"),
    ("KebijakanMoneter", "ig_ekonomi"),
    ("Makroprudensial", "ig_ekonomi"),
    ("SistemPembayaran", "ig_ekonomi"),
    ("EkonomiSyariah", "ig_ekonomi"),
    ("KeuanganInklusif", "ig_ekonomi"),
    ("KetahananPangan", "ig_ekonomi"),
    ("GPIPSBali", "ig_ekonomi"),
    # 3. Digitalisasi & Pembayaran (QRIS)
    ("QRIS", "ig_qris"),
    ("PakeQRIS", "ig_qris"),
    ("QRISBali", "ig_qris"),
    ("DigitalisasiSistemPembayaran", "ig_qris"),
    ("CashlessSociety", "ig_qris"),
    ("TransaksiDigital", "ig_qris"),
    ("BIFAST", "ig_qris"),
    ("BayarPakaiQRIS", "ig_qris"),
    ("EkosistemDigital", "ig_qris"),
    ("TransformasiDigital", "ig_qris"),
    ("PembayaranNonTunai", "ig_qris"),
    ("FintechIndonesia", "ig_qris"),
    ("DigitalPayment", "ig_qris"),
    ("SmartEconomy", "ig_qris"),
    ("EkonomiDigital", "ig_qris"),
    # 4. UMKM & Pemberdayaan
    ("UMKMBali", "ig_umkm"),
    ("UMKMNaikKelas", "ig_umkm"),
    ("UMKMGoDigital", "ig_umkm"),
    ("UMKMGoGlobal", "ig_umkm"),
    ("BinaanBI", "ig_umkm"),
    ("ProdukLokalBali", "ig_umkm"),
    ("KaryaAnakBangsa", "ig_umkm"),
    ("EkonomiKreatifBali", "ig_umkm"),
    ("UMKMIndonesia", "ig_umkm"),
    ("PemberdayaanUMKM", "ig_umkm"),
    ("KaryaBali", "ig_umkm"),
    ("WirausahaMuda", "ig_umkm"),
    ("InovasiUMKM", "ig_umkm"),
    ("UMKMBerdaya", "ig_umkm"),
    # 5. Pariwisata & Komunitas Bali
    ("InfoBali", "ig_bali"),
    ("ExploreBali", "ig_bali"),
    ("EventBali", "ig_bali"),
    ("BeritaBali", "ig_bali"),
    ("BaliTerkini", "ig_bali"),
    ("DenpasarNow", "ig_bali"),
    ("RenonBali", "ig_bali"),
    ("WonderfulIndonesia", "ig_bali"),
    ("PesonaIndonesia", "ig_bali"),
    ("BaliLife", "ig_bali"),
    ("KomunitasBali", "ig_bali"),
    ("SosialMediaBali", "ig_bali"),
    ("UpdateBali", "ig_bali"),
    ("LocalPrideBali", "ig_bali"),
    ("BaliEvent", "ig_bali"),
    # 6. Edukasi & Engagement
    ("EdukasiKeuangan", "ig_edukasi"),
    ("LiterasiKeuangan", "ig_edukasi"),
    ("CerdasFinansial", "ig_edukasi"),
    ("TipsKeuangan", "ig_edukasi"),
    ("InvestasiBijak", "ig_edukasi"),
    ("InfoEkonomi", "ig_edukasi"),
    ("PendidikanEkonomi", "ig_edukasi"),
    ("BijakBerbelanja", "ig_edukasi"),
    ("HariRupiah", "ig_edukasi"),
    ("BankSentralRI", "ig_edukasi"),
    ("FaktaEkonomi", "ig_edukasi"),
    ("EkonomiIndonesia", "ig_edukasi"),
    ("InspirasiBisnis", "ig_edukasi"),
    ("GenerasiQRIS", "ig_edukasi"),
    ("SadarkanRupiah", "ig_edukasi"),
    # 7. Tambahan / Trending
    ("BicaraBI", "ig_trending"),
    ("BankIndonesiaBicara", "ig_trending"),
    ("SinergiUntukNegeri", "ig_trending"),
    ("BaliMembangun", "ig_trending"),
    ("EkonomiBaliBangkit", "ig_trending"),
    ("DigitalBali", "ig_trending"),
    ("InovasiSistemPembayaran", "ig_trending"),
    ("KetahananPanganBali", "ig_trending"),
    ("PariwisataBali", "ig_trending"),
    ("KedaulatanRupiah", "ig_trending"),
]

# Priority order for Graph API sync (rate limit ~30 unique hashtags / 7 days).
INSTAGRAM_PRIORITY_HASHTAGS: List[str] = [
    "BIBali",
    "BankIndonesiaBali",
    "KantorPerwakilanBIBali",
    "BankIndonesia",
    "QRISBali",
    "InflasiBali",
    "EkonomiBali",
    "UMKMBali",
    "TPIDBali",
    "GPIPSBali",
    "PakeQRIS",
    "QRIS",
    "CintaBanggaPahamRupiah",
    "CBPR",
    "BicaraBI",
    "PengendalianInflasi",
    "SistemPembayaran",
    "UMKMNaikKelas",
    "EkonomiBaliBangkit",
    "DigitalBali",
    "RenonBali",
    "InfoBali",
    "BeritaBali",
    "LiterasiKeuangan",
    "EdukasiKeuangan",
    "BIFAST",
    "BayarPakaiQRIS",
    "BinaanBI",
    "PariwisataBali",
    "KedaulatanRupiah",
]

HASHTAG_CATEGORY_LABELS = {
    "ig_branding": "Branding Bank Indonesia",
    "ig_ekonomi": "Ekonomi & Kebijakan Daerah",
    "ig_qris": "Digitalisasi & QRIS",
    "ig_umkm": "UMKM & Pemberdayaan",
    "ig_bali": "Pariwisata & Komunitas Bali",
    "ig_edukasi": "Edukasi & Engagement",
    "ig_trending": "Trending / Variatif",
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

"""Insight engine: trend analysis, correlation, and economic explanations."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import pearsonr

from data_loader import _period_sort_key, pivot_growth


@dataclass
class TrendInfo:
    direction: str  # naik, turun, stabil
    latest_value: float
    previous_value: float | None
    change: float | None
    avg_recent: float


@dataclass
class RelationshipInsight:
    other_subject: str
    correlation: float
    other_trend: str
    relationship: str  # berbanding terbalik, searah, lemah
    explanation: str


# Domain knowledge for Bali / PDRB sectors (Indonesian).
ECONOMIC_CONTEXT: dict[tuple[str, str], str] = {
    ("pariwisata", "pertanian"): (
        "Sektor pariwisata dan pertanian sering bergerak berlawanan dalam struktur ekonomi Bali. "
        "Ketika kunjungan wisata dan permintaan akomodasi meningkat, tenaga kerja dan investasi "
        "cenderung bergeser ke jasa wisata sehingga pertumbuhan pertanian relatif melambat."
    ),
    ("akomodasi", "pertanian"): (
        "Boom pariwiswa mendorong alokasi sumber daya ke hotel dan restoran. "
        "Lahan dan tenaga kerja yang teralih ke sektor jasa dapat menekan ekspansi produksi pertanian."
    ),
    ("ekspor", "impor"): (
        "Kenaikan ekspor barang/jasa Bali biasanya didukung impor bahan baku dan kapital. "
        "Namun jika pertumbuhan ekspor didorong permintaan domestik, impor bisa justru tertekan sementara."
    ),
    ("konsumsi pemerintah", "konsumsi rumah tangga"): (
        "Fiskal expansif (belanja pemerintah naik) dapat menstimulus ekonomi jangka pendek, "
        "tetapi jika sumber daya terbatas, crowding-out bisa muncul dan konsumsi rumah tangga melambat."
    ),
    ("konstruksi", "real estat"): (
        "Pertumbuhan konstruksi yang tinggi sering diikuti normalisasi sektor real estat "
        "karena pipeline proyek habis atau oversupply properti wisata."
    ),
    ("transportasi", "pariwisata"): (
        "Transportasi dan pariwisata cenderung bergerak searah: lebih banyak wisatawan "
        "meningkatkan permintaan penerbangan, darat, dan logistik."
    ),
    ("jasa keuangan", "konstruksi"): (
        "Kredit investasi properti/infrastruktur mendorong konstruksi. "
        "Jika jasa keuangan melambat (ketatnya kredit), pertumbuhan konstruksi ikut tertekan."
    ),
}


def _normalize_keyword(text: str) -> str:
    return text.lower().strip()


def _match_context(subject_a: str, subject_b: str) -> str | None:
    a = _normalize_keyword(subject_a)
    b = _normalize_keyword(subject_b)
    keys = list(ECONOMIC_CONTEXT.keys())
    for left, right in keys:
        if (left in a and right in b) or (left in b and right in a):
            return ECONOMIC_CONTEXT[(left, right)]
    return None


def analyze_trend(series: pd.Series, recent_n: int = 4) -> TrendInfo:
    clean = series.dropna()
    if clean.empty:
        return TrendInfo("stabil", 0.0, None, None, 0.0)

    latest = float(clean.iloc[-1])
    previous = float(clean.iloc[-2]) if len(clean) >= 2 else None
    change = latest - previous if previous is not None else None
    recent = clean.tail(recent_n)
    avg_recent = float(recent.mean())

    if change is None:
        direction = "stabil"
    elif change > 0.15:
        direction = "naik"
    elif change < -0.15:
        direction = "turun"
    else:
        direction = "stabil"

    return TrendInfo(direction, latest, previous, change, avg_recent)


def _relationship_label(corr: float) -> str:
    if corr <= -0.45:
        return "berbanding terbalik"
    if corr >= 0.45:
        return "searah"
    return "lemah"


def _generic_explanation(
    selected: str,
    other: str,
    selected_trend: str,
    other_trend: str,
    corr: float,
    relationship: str,
) -> str:
    if relationship == "berbanding terbalik":
        if selected_trend == "naik" and other_trend == "turun":
            return (
                f"Ketika **{selected}** menunjukkan tren **naik**, **{other}** cenderung **turun** "
                f"(korelasi {corr:.2f}). Pola ini sering muncul karena pergeseran sumber daya antarsektor, "
                f"perubahan komposisi permintaan, atau efek musiman di ekonomi Bali."
            )
        if selected_trend == "turun" and other_trend == "naik":
            return (
                f"Penurunan **{selected}** beriringan dengan kenaikan **{other}** "
                f"(korelasi {corr:.2f}). Artinya, saat tekanan pada sektor utama membaik/melemah, "
                f"sektor lain mengisi gap permintaan atau menyerap alokasi investasi."
            )
        return (
            f"**{selected}** dan **{other}** memiliki hubungan berbanding terbalik (korelasi {corr:.2f}). "
            f"Kenaikan satu indikator historisnya diikuti penurunan indikator lainnya."
        )

    if relationship == "searah":
        return (
            f"**{selected}** dan **{other}** bergerak **searah** (korelasi {corr:.2f}). "
            f"Keduanya dipengaruhi faktor ekonomi makro yang sama—misalnya siklus pariwisata, "
            f"kebijakan fiskal, atau kondisi permintaan global."
        )

    return (
        f"Hubungan **{selected}** dengan **{other}** relatif lemah (korelasi {corr:.2f}), "
        f"sehingga pergerakan keduanya lebih independen dalam periode data ini."
    )


def generate_insights(
    growth_df: pd.DataFrame,
    selected_subject: str,
    min_periods: int = 4,
    top_n: int = 5,
) -> tuple[TrendInfo, list[RelationshipInsight]]:
    wide = pivot_growth(growth_df)
    if selected_subject not in wide.index:
        raise ValueError(f"Subyek '{selected_subject}' tidak ditemukan.")

    selected_series = wide.loc[selected_subject]
    selected_trend = analyze_trend(selected_series)

    insights: list[RelationshipInsight] = []
    for other in wide.index:
        if other == selected_subject:
            continue

        pair = pd.concat([selected_series, wide.loc[other]], axis=1, join="inner").dropna()
        if len(pair) < min_periods:
            continue

        corr, _ = pearsonr(pair.iloc[:, 0], pair.iloc[:, 1])
        if np.isnan(corr):
            continue

        other_trend = analyze_trend(wide.loc[other])
        relationship = _relationship_label(corr)
        context = _match_context(selected_subject, other)
        explanation = context or _generic_explanation(
            selected_subject,
            other,
            selected_trend.direction,
            other_trend.direction,
            corr,
            relationship,
        )

        insights.append(
            RelationshipInsight(
                other_subject=other,
                correlation=float(corr),
                other_trend=other_trend.direction,
                relationship=relationship,
                explanation=explanation,
            )
        )

    # Prioritize strong inverse/positive links and those matching current trend pattern.
    def rank(item: RelationshipInsight) -> tuple:
        trend_bonus = 0
        if selected_trend.direction == "naik" and item.other_trend == "turun" and item.correlation < 0:
            trend_bonus = 2
        if selected_trend.direction == "turun" and item.other_trend == "naik" and item.correlation < 0:
            trend_bonus = 2
        return (trend_bonus, abs(item.correlation))

    insights.sort(key=rank, reverse=True)
    return selected_trend, insights[:top_n]


def summarize_selected_subject(selected_subject: str, trend: TrendInfo, periods: list[str]) -> str:
    arrow = {"naik": "↑", "turun": "↓", "stabil": "→"}[trend.direction]
    change_text = ""
    if trend.change is not None:
        change_text = f" Perubahan terakhir: {trend.change:+.2f} poin."
    return (
        f"**{selected_subject}** saat ini **{trend.direction}** {arrow} "
        f"dengan nilai terakhir **{trend.latest_value:.2f}%**.{change_text} "
        f"Rata-rata {min(4, len(periods))} periode terakhir: **{trend.avg_recent:.2f}%**."
    )

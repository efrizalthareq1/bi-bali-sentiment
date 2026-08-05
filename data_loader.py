"""Flexible Excel loader for Bali PDRB / indicator workbooks."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

DEFAULT_EXCEL_PATH = Path(r"c:\Users\user\Downloads\Prompt Indikator Bali_NEW.xlsx")

PDRB_KEYWORDS = re.compile(
    r"pdrb|pertumbuhan|growth|laju|yoy|y-o-y|ekonomi|gdp|triwulan|kuartal|quarter",
    re.I,
)

LABEL_KEYWORDS = (
    "indikator",
    "variabel",
    "subject",
    "keterangan",
    "uraian",
    "deskripsi",
    "nama",
    "lapangan usaha",
    "komponen",
    "sektor",
)

PERIOD_PATTERNS = (
    re.compile(r"^(19|20)\d{2}$"),
    re.compile(r"^triwulan\s*[ivx\d]+[\s\-/]*(19|20)?\d{2,4}$", re.I),
    re.compile(r"^q[1-4][\s\-/]*(19|20)?\d{2,4}$", re.I),
    re.compile(r"^(19|20)\d{2}[\s\-/]*q[1-4]$", re.I),
    re.compile(r"^t[1-4][\s\-/]*(19|20)?\d{2,4}$", re.I),
    re.compile(r"^(19|20)\d{2}[\s\-/]*t[1-4]$", re.I),
    re.compile(r"^semester\s*[12][\s\-/]*(19|20)?\d{2,4}$", re.I),
)


@dataclass
class SheetMeta:
    name: str
    pdrb_related: bool
    header_row: int
    label_col: str
    period_cols: list[str]
    row_count: int


@dataclass
class LoadedWorkbook:
    path: str
    sheets: list[SheetMeta] = field(default_factory=list)
    long_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    growth_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    subjects: list[str] = field(default_factory=list)
    periods: list[str] = field(default_factory=list)


def _norm(value: Any) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text if text else None


def _is_period_column(name: str) -> bool:
    cleaned = str(name).strip()
    if not cleaned or cleaned.lower().startswith("unnamed"):
        return False
    return any(p.search(cleaned) for p in PERIOD_PATTERNS)


def _detect_header_row(raw: pd.DataFrame) -> int:
    best_row = 0
    best_score = -1
    for idx in range(min(25, len(raw))):
        row = raw.iloc[idx]
        non_null = sum(1 for x in row if _norm(x) is not None)
        period_hits = sum(1 for x in row if _norm(x) and _is_period_column(str(x)))
        label_hits = sum(
            1
            for x in row
            if _norm(x) and any(k in str(x).lower() for k in LABEL_KEYWORDS)
        )
        score = non_null + period_hits * 3 + label_hits * 2
        if score > best_score:
            best_score = score
            best_row = idx
    return best_row


def _pick_label_column(df: pd.DataFrame) -> str:
    for col in df.columns:
        col_lower = str(col).lower()
        if any(k in col_lower for k in LABEL_KEYWORDS):
            return str(col)

    object_cols = []
    for col in df.columns:
        series = df[col].dropna().astype(str)
        if series.empty:
            continue
        avg_len = series.str.len().mean()
        numeric_ratio = pd.to_numeric(series, errors="coerce").notna().mean()
        if numeric_ratio < 0.3 and avg_len > 4:
            object_cols.append((col, avg_len))

    if object_cols:
        object_cols.sort(key=lambda item: item[1], reverse=True)
        return str(object_cols[0][0])

    return str(df.columns[0])


def _to_numeric(value: Any) -> float | None:
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text or text.lower() in {"-", "na", "n/a"}:
        return None
    text = text.replace("%", "").replace(",", ".")
    text = re.sub(r"[^\d.\-]", "", text)
    try:
        return float(text)
    except ValueError:
        return None


def _sheet_is_pdrb_related(name: str, df: pd.DataFrame) -> bool:
    blob = name + " " + " ".join(str(c) for c in df.columns[:40])
    sample = " ".join(df.head(20).astype(str).values.flatten())
    return bool(PDRB_KEYWORDS.search(blob + " " + sample))


def _looks_like_growth(name: str, values: pd.Series) -> bool:
    blob = name.lower()
    if any(k in blob for k in ("pertumbuhan", "laju", "growth", "yoy", "y-on-y", "q-to-q")):
        return True
    nums = values.dropna().map(_to_numeric).dropna()
    if nums.empty:
        return False
    # Growth rates in Indonesian stats are usually between -100 and 100.
    return nums.between(-100, 100).mean() > 0.8 and nums.abs().median() < 40


def _melt_sheet(name: str, df: pd.DataFrame, label_col: str, period_cols: list[str]) -> pd.DataFrame:
    keep = [label_col] + period_cols
    subset = df[keep].copy()
    subset[label_col] = subset[label_col].astype(str).str.strip()
    subset = subset[subset[label_col].notna() & (subset[label_col] != "") & (subset[label_col] != "nan")]

    long_df = subset.melt(
        id_vars=[label_col],
        var_name="periode",
        value_name="nilai",
    )
    long_df["nilai"] = long_df["nilai"].map(_to_numeric)
    long_df = long_df.dropna(subset=["nilai"])
    long_df["sheet"] = name
    long_df = long_df.rename(columns={label_col: "subyek"})
    long_df["subyek"] = long_df["subyek"].str.strip()
    long_df["periode"] = long_df["periode"].astype(str).str.strip()
    return long_df


def load_workbook(path: str | Path | None = None) -> LoadedWorkbook:
    file_path = Path(path) if path else DEFAULT_EXCEL_PATH
    if not file_path.exists():
        raise FileNotFoundError(f"File Excel tidak ditemukan: {file_path}")

    xl = pd.ExcelFile(file_path)
    all_long: list[pd.DataFrame] = []
    metas: list[SheetMeta] = []

    for sheet_name in xl.sheet_names:
        raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
        if raw.empty:
            continue

        header_row = _detect_header_row(raw)
        df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row)
        df = df.dropna(axis=1, how="all")
        if df.empty:
            continue

        label_col = _pick_label_column(df)
        period_cols = [str(c) for c in df.columns if _is_period_column(str(c))]
        if not period_cols:
            continue

        related = _sheet_is_pdrb_related(sheet_name, df)
        metas.append(
            SheetMeta(
                name=sheet_name,
                pdrb_related=related,
                header_row=header_row,
                label_col=label_col,
                period_cols=period_cols,
                row_count=len(df),
            )
        )
        all_long.append(_melt_sheet(sheet_name, df, label_col, period_cols))

    if not all_long:
        raise ValueError("Tidak ada data periode yang bisa dibaca dari workbook.")

    long_df = pd.concat(all_long, ignore_index=True)
    long_df = long_df.drop_duplicates(subset=["sheet", "subyek", "periode"], keep="last")

    growth_parts: list[pd.DataFrame] = []
    for sheet_name, group in long_df.groupby("sheet"):
        sample_values = group["nilai"]
        if _looks_like_growth(sheet_name, sample_values) or any(
            m.name == sheet_name and m.pdrb_related for m in metas
        ):
            growth_parts.append(group)

    if growth_parts:
        growth_df = pd.concat(growth_parts, ignore_index=True)
    else:
        growth_df = long_df.copy()

    growth_df = growth_df[growth_df["subyek"].str.len() > 1]
    growth_df = growth_df.sort_values(["subyek", "periode"])

    subjects = sorted(growth_df["subyek"].unique().tolist())
    periods = sorted(growth_df["periode"].unique().tolist(), key=_period_sort_key)

    return LoadedWorkbook(
        path=str(file_path),
        sheets=metas,
        long_df=long_df,
        growth_df=growth_df,
        subjects=subjects,
        periods=periods,
    )


def _period_sort_key(period: str) -> tuple:
    text = str(period).strip().lower()
    year_match = re.search(r"(19|20)\d{2}", text)
    year = int(year_match.group()) if year_match else 0

    quarter = 0
    if re.search(r"triwulan\s*iv|q4|t4|\s4", text):
        quarter = 4
    elif re.search(r"triwulan\s*iii|q3|t3|\s3", text):
        quarter = 3
    elif re.search(r"triwulan\s*ii|q2|t2|\s2", text):
        quarter = 2
    elif re.search(r"triwulan\s*i[^i]|q1|t1|\s1", text):
        quarter = 1

    semester = 0
    if "semester 2" in text or "semester ii" in text:
        semester = 2
    elif "semester 1" in text or "semester i" in text:
        semester = 1

    return (year, semester, quarter, text)


def pivot_growth(growth_df: pd.DataFrame) -> pd.DataFrame:
    wide = growth_df.pivot_table(
        index="subyek",
        columns="periode",
        values="nilai",
        aggfunc="last",
    )
    ordered_cols = sorted(wide.columns.tolist(), key=_period_sort_key)
    return wide[ordered_cols]


def get_subject_series(growth_df: pd.DataFrame, subject: str) -> pd.Series:
    subset = growth_df[growth_df["subyek"] == subject].copy()
    subset["_sort"] = subset["periode"].map(_period_sort_key)
    subset = subset.sort_values("_sort")
    return subset.set_index("periode")["nilai"]

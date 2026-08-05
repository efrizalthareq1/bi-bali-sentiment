"""Dashboard Pertumbuhan PDRB Bali dengan Insight Otomatis."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_loader import (
    DEFAULT_EXCEL_PATH,
    LoadedWorkbook,
    _period_sort_key,
    get_subject_series,
    load_workbook,
    pivot_growth,
)
from insights import generate_insights, summarize_selected_subject

st.set_page_config(
    page_title="Dashboard Pertumbuhan PDRB Bali",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        color: #1a365d;
        margin-bottom: 0.25rem;
    }
    .sub-header {
        color: #4a5568;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.2rem;
        border-radius: 12px;
        color: white;
        text-align: center;
    }
    .insight-box {
        background: #f7fafc;
        border-left: 4px solid #4299e1;
        padding: 1rem 1.2rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 0.8rem;
    }
    .insight-inverse {
        border-left-color: #ed8936;
    }
    .insight-positive {
        border-left-color: #48bb78;
    }
    div[data-testid="stMetric"] {
        background: #edf2f7;
        padding: 0.8rem;
        border-radius: 10px;
    }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


@st.cache_data(show_spinner="Memuat data Excel...")
def cached_load(path: str) -> LoadedWorkbook:
    return load_workbook(path)


def trend_color(direction: str) -> str:
    return {"naik": "#38a169", "turun": "#e53e3e", "stabil": "#718096"}.get(direction, "#718096")


def resolve_excel_path() -> Path:
    uploaded = st.session_state.get("excel_upload")
    if uploaded is not None:
        temp_path = Path("data") / uploaded.name
        temp_path.parent.mkdir(exist_ok=True)
        temp_path.write_bytes(uploaded.getbuffer())
        return temp_path
    return DEFAULT_EXCEL_PATH


def filter_workbook(workbook: LoadedWorkbook, sheet_filter: str) -> LoadedWorkbook:
    if sheet_filter == "Semua sheet":
        return workbook
    growth_df = workbook.growth_df[workbook.growth_df["sheet"] == sheet_filter].copy()
    return LoadedWorkbook(
        path=workbook.path,
        sheets=[s for s in workbook.sheets if s.name == sheet_filter],
        long_df=workbook.long_df[workbook.long_df["sheet"] == sheet_filter],
        growth_df=growth_df,
        subjects=sorted(growth_df["subyek"].unique().tolist()),
        periods=sorted(growth_df["periode"].unique().tolist(), key=_period_sort_key),
    )


def main() -> None:
    st.markdown('<p class="main-header">📊 Dashboard Pertumbuhan PDRB Bali</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Analisis tren pertumbuhan ekonomi dengan insight otomatis antar sektor</p>',
        unsafe_allow_html=True,
    )

    st.sidebar.header("⚙️ Pengaturan")
    st.session_state["excel_upload"] = st.sidebar.file_uploader(
        "Upload file Excel (opsional)",
        type=["xlsx", "xls"],
        help="Kosongkan untuk memakai file default di Downloads.",
    )
    excel_path = resolve_excel_path()
    st.sidebar.caption(f"File: `{excel_path}`")

    try:
        workbook = cached_load(str(excel_path))
    except FileNotFoundError:
        st.error(
            f"File Excel tidak ditemukan di `{DEFAULT_EXCEL_PATH}`. "
            "Silakan upload file melalui sidebar."
        )
        st.stop()
    except Exception as exc:
        st.error(f"Gagal memuat data: {exc}")
        st.stop()

    with st.sidebar:
        st.divider()
        sheet_options = ["Semua sheet"] + [s.name for s in workbook.sheets]
        sheet_filter = st.selectbox("Filter sheet", sheet_options)
        filtered = filter_workbook(workbook, sheet_filter)
        subjects = filtered.subjects
        selected_subject = st.selectbox("Pilih subyek / indikator", subjects)
        compare_subjects = st.multiselect(
            "Bandingkan dengan (opsional)",
            [s for s in subjects if s != selected_subject],
            max_selections=4,
        )

    if not selected_subject:
        st.warning("Tidak ada subyek yang tersedia.")
        st.stop()

    growth_df = filtered.growth_df
    wide = pivot_growth(growth_df)
    selected_series = get_subject_series(growth_df, selected_subject)
    selected_trend, relationship_insights = generate_insights(growth_df, selected_subject)

    # --- KPI Row ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Nilai Terakhir", f"{selected_trend.latest_value:.2f}%")
    with col2:
        delta = f"{selected_trend.change:+.2f}%" if selected_trend.change is not None else None
        st.metric("Perubahan", f"{selected_trend.direction.title()}", delta=delta)
    with col3:
        st.metric("Rata-rata Terakhir", f"{selected_trend.avg_recent:.2f}%")
    with col4:
        st.metric("Jumlah Periode", len(selected_series.dropna()))

    st.divider()

    # --- Charts ---
    chart_col, table_col = st.columns([2, 1])

    with chart_col:
        st.subheader(f"Tren Pertumbuhan: {selected_subject}")

        plot_subjects = [selected_subject, *compare_subjects]
        plot_df = wide.loc[plot_subjects].reset_index().melt(
            id_vars="subyek", var_name="periode", value_name="nilai"
        )
        plot_df["_sort"] = plot_df["periode"].map(_period_sort_key)
        plot_df = plot_df.sort_values("_sort")

        fig = px.line(
            plot_df,
            x="periode",
            y="nilai",
            color="subyek",
            markers=True,
            labels={"periode": "Periode", "nilai": "Pertumbuhan (%)", "subyek": "Subyek"},
        )
        fig.update_layout(
            hovermode="x unified",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            height=420,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        fig.add_hline(y=0, line_dash="dash", line_color="#a0aec0", opacity=0.6)
        st.plotly_chart(fig, use_container_width=True)

        # Bar chart latest period comparison
        latest_period = sorted(wide.columns.tolist(), key=_period_sort_key)[-1]
        latest_vals = wide[latest_period].dropna().sort_values(ascending=True).tail(12)
        bar_fig = px.bar(
            x=latest_vals.values,
            y=latest_vals.index,
            orientation="h",
            labels={"x": "Pertumbuhan (%)", "y": "Subyek"},
            title=f"Top subyek — periode {latest_period}",
            color=latest_vals.values,
            color_continuous_scale="RdYlGn",
        )
        bar_fig.update_layout(height=380, showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(bar_fig, use_container_width=True)

    with table_col:
        st.subheader("Ringkasan Sheet")
        meta_rows = [
            {
                "Sheet": s.name,
                "PDRB": "✓" if s.pdrb_related else "-",
                "Baris": s.row_count,
                "Periode": len(s.period_cols),
            }
            for s in filtered.sheets
        ]
        st.dataframe(pd.DataFrame(meta_rows), hide_index=True, use_container_width=True)

        st.subheader("Data Subyek Terpilih")
        show_df = selected_series.reset_index()
        show_df.columns = ["Periode", "Pertumbuhan (%)"]
        st.dataframe(show_df, hide_index=True, use_container_width=True, height=320)

    st.divider()

    # --- Insights Section ---
    st.subheader("💡 Insight Otomatis")
    st.markdown(summarize_selected_subject(selected_subject, selected_trend, filtered.periods))

    if not relationship_insights:
        st.info("Belum cukup data periode untuk menghasilkan insight korelasi.")
    else:
        st.markdown("#### Hubungan dengan subyek lain")
        for item in relationship_insights:
            css_class = "insight-box"
            if item.relationship == "berbanding terbalik":
                css_class += " insight-inverse"
                icon = "↔️"
            elif item.relationship == "searah":
                css_class += " insight-positive"
                icon = "↗️"
            else:
                icon = "〰️"

            header = (
                f"{icon} **{selected_subject}** ↔ **{item.other_subject}** — "
                f"{item.relationship.title()} (r = {item.correlation:.2f}) | "
                f"Tren lain: **{item.other_trend}**"
            )
            st.markdown(
                f'<div class="{css_class}">{header}<br><br>{item.explanation}</div>',
                unsafe_allow_html=True,
            )

    # --- Correlation heatmap for top subjects ---
    st.subheader("🗺️ Peta Korelasi")
    top_subjects = wide.mean(axis=1).abs().sort_values(ascending=False).head(min(15, len(wide))).index
    corr = wide.loc[top_subjects].T.corr()

    heatmap = go.Figure(
        data=go.Heatmap(
            z=corr.values,
            x=corr.columns,
            y=corr.index,
            colorscale="RdBu",
            zmid=0,
            zmin=-1,
            zmax=1,
            text=corr.values.round(2),
            texttemplate="%{text}",
        )
    )
    heatmap.update_layout(
        height=max(420, len(top_subjects) * 28),
        xaxis_tickangle=-45,
        margin=dict(l=120, b=120),
    )
    st.plotly_chart(heatmap, use_container_width=True)

    with st.expander("📋 Lihat semua data pertumbuhan"):
        st.dataframe(wide.reset_index(), use_container_width=True)


if __name__ == "__main__":
    main()

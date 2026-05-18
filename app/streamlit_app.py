from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd
import streamlit as st

try:
    import plotly.express as px
except Exception:  # pragma: no cover - app should still open without plotly
    px = None

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed"
REPORTS_DIR = ROOT / "reports"

DATASETS = {
    "wallet_swaps": DATA_DIR / "wallet_swaps.csv",
    "trades_paired": DATA_DIR / "trades_paired.csv",
    "latency_sim": DATA_DIR / "latency_sim.csv",
    "fee_adjusted_pnl": DATA_DIR / "fee_adjusted_pnl.csv",
    "copy_stress_model": DATA_DIR / "copy_stress_model.csv",
    "entry_context": DATA_DIR / "entry_context.csv",
    "trigger_tests": DATA_DIR / "trigger_tests.csv",
    "open_positions": DATA_DIR / "open_positions.csv",
}


st.set_page_config(
    page_title="membot forensic app",
    page_icon="🧪",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def load_csv(path: str) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(csv_path)
    except Exception as exc:
        return pd.DataFrame({"_load_error": [str(exc)]})


def dataset_status() -> pd.DataFrame:
    rows = []
    for name, path in DATASETS.items():
        exists = path.exists()
        rows.append(
            {
                "dataset": name,
                "path": str(path.relative_to(ROOT)),
                "exists": exists,
                "bytes": path.stat().st_size if exists else 0,
                "rows": len(load_csv(str(path))) if exists else 0,
            }
        )
    return pd.DataFrame(rows)


def find_col(df: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    existing = set(df.columns)
    for col in candidates:
        if col in existing:
            return col
    return None


def metric_number(value: object, fallback: str = "—") -> str:
    if value is None:
        return fallback
    try:
        if pd.isna(value):
            return fallback
    except Exception:
        pass
    if isinstance(value, float):
        return f"{value:,.4f}".rstrip("0").rstrip(".")
    return str(value)


def render_missing(name: str, path: Path) -> None:
    st.info(
        f"`{name}` не найден: `{path.relative_to(ROOT)}`. "
        "Сначала запусти pipeline или положи CSV в `data/processed/`."
    )


def pnl_column(df: pd.DataFrame) -> str | None:
    return find_col(
        df,
        [
            "net_pnl_sol",
            "pnl_sol",
            "gross_pnl_sol",
            "net_pnl_usd",
            "copy_net_pnl_usd",
            "verified_fifo_unrealized_pnl_usd",
        ],
    )


def render_overview() -> None:
    status = dataset_status()
    st.subheader("Data health")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Datasets present", int(status["exists"].sum()))
    c2.metric("Known datasets", len(status))
    c3.metric("Total rows", int(status["rows"].sum()))
    c4.metric("Total bytes", int(status["bytes"].sum()))
    st.dataframe(status, use_container_width=True, hide_index=True)

    swaps = load_csv(str(DATASETS["wallet_swaps"]))
    paired = load_csv(str(DATASETS["trades_paired"]))

    st.subheader("Pipeline snapshot")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("wallet_swaps rows", len(swaps) if not swaps.empty else 0)
    k2.metric("paired trades", len(paired) if not paired.empty else 0)

    side_col = find_col(swaps, ["side", "swap_side"])
    if side_col and not swaps.empty:
        k3.metric("BUY rows", int((swaps[side_col].astype(str).str.upper() == "BUY").sum()))
        k4.metric("SELL rows", int((swaps[side_col].astype(str).str.upper() == "SELL").sum()))
    else:
        k3.metric("BUY rows", "—")
        k4.metric("SELL rows", "—")

    pcol = pnl_column(paired)
    if pcol and not paired.empty:
        wins = (pd.to_numeric(paired[pcol], errors="coerce") > 0).sum()
        total = pd.to_numeric(paired[pcol], errors="coerce").sum()
        st.metric("Paired total PnL", metric_number(float(total)))
        st.metric("Win rate", f"{wins / max(1, len(paired)):.1%}")


def render_swaps() -> None:
    df = load_csv(str(DATASETS["wallet_swaps"]))
    if df.empty:
        render_missing("wallet_swaps", DATASETS["wallet_swaps"])
        return

    st.subheader("Normalized wallet swaps")
    side_col = find_col(df, ["side", "swap_side"])
    confidence_col = find_col(df, ["parse_confidence", "confidence"])

    c1, c2, c3 = st.columns(3)
    c1.metric("Rows", len(df))
    c2.metric("Unique mints", df["token_mint"].nunique() if "token_mint" in df.columns else "—")
    c3.metric("Failed rows", int((df[side_col].astype(str).str.upper() == "FAILED").sum()) if side_col else "—")

    if side_col and px is not None:
        st.plotly_chart(px.histogram(df, x=side_col, title="Side distribution"), use_container_width=True)
    if confidence_col and px is not None:
        st.plotly_chart(px.histogram(df, x=confidence_col, title="Parse confidence"), use_container_width=True)

    st.dataframe(df.head(500), use_container_width=True)


def render_trades() -> None:
    df = load_csv(str(DATASETS["trades_paired"]))
    if df.empty:
        render_missing("trades_paired", DATASETS["trades_paired"])
        return

    st.subheader("Paired FIFO trades")
    pcol = pnl_column(df)
    hold_col = find_col(df, ["hold_seconds", "holding_seconds"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Trades", len(df))
    if pcol:
        pnl = pd.to_numeric(df[pcol], errors="coerce")
        c2.metric("Total PnL", metric_number(float(pnl.sum())))
        c3.metric("Win rate", f"{(pnl > 0).sum() / max(1, pnl.notna().sum()):.1%}")
        c4.metric("Profit factor", metric_number(pnl[pnl > 0].sum() / abs(pnl[pnl < 0].sum()) if (pnl < 0).any() else None))
    else:
        c2.metric("Total PnL", "—")
        c3.metric("Win rate", "—")
        c4.metric("Profit factor", "—")

    if pcol and px is not None:
        st.plotly_chart(px.histogram(df, x=pcol, nbins=80, title="PnL distribution"), use_container_width=True)
    if hold_col and px is not None:
        st.plotly_chart(px.histogram(df, x=hold_col, nbins=80, title="Hold seconds distribution"), use_container_width=True)

    st.dataframe(df.head(500), use_container_width=True)


def render_latency_and_copy() -> None:
    st.subheader("Latency / copy-stress")
    for name in ["latency_sim", "copy_stress_model", "fee_adjusted_pnl"]:
        path = DATASETS[name]
        df = load_csv(str(path))
        with st.expander(name, expanded=not df.empty):
            if df.empty:
                render_missing(name, path)
                continue
            st.dataframe(df.head(500), use_container_width=True)
            scenario_col = find_col(df, ["scenario", "delay_label"])
            pcol = pnl_column(df)
            if scenario_col and pcol and px is not None:
                plot_df = df.copy()
                plot_df[pcol] = pd.to_numeric(plot_df[pcol], errors="coerce")
                grouped = plot_df.groupby(scenario_col, as_index=False)[pcol].sum()
                st.plotly_chart(px.bar(grouped, x=scenario_col, y=pcol, title=f"{name}: PnL by scenario"), use_container_width=True)


def render_entry_context() -> None:
    st.subheader("Entry context / trigger tests")
    for name in ["entry_context", "trigger_tests"]:
        path = DATASETS[name]
        df = load_csv(str(path))
        with st.expander(name, expanded=not df.empty):
            if df.empty:
                render_missing(name, path)
                continue
            st.dataframe(df.head(500), use_container_width=True)


def render_reports() -> None:
    st.subheader("Markdown reports")
    if not REPORTS_DIR.exists():
        st.info("`reports/` пока не найден.")
        return
    reports = sorted(REPORTS_DIR.glob("*.md"))
    if not reports:
        st.info("В `reports/` пока нет `.md` отчётов.")
        return
    selected = st.selectbox("Report", [str(p.relative_to(ROOT)) for p in reports])
    report_path = ROOT / selected
    st.markdown(report_path.read_text(encoding="utf-8", errors="replace"))


def main() -> None:
    st.title("membot forensic app")
    st.caption("Read-only dashboard for Solana wallet replay outputs. No trading. No private keys.")

    with st.sidebar:
        st.header("Guardrails")
        st.write("✅ Reads local CSV/MD artifacts")
        st.write("✅ No private keys")
        st.write("✅ No trading execution")
        st.write("⚠️ Dashboard metrics are not final algorithm claims")
        if st.button("Clear cache"):
            st.cache_data.clear()
            st.rerun()

    tabs = st.tabs([
        "Overview",
        "Swaps",
        "Paired trades",
        "Latency / copy",
        "Entry context",
        "Reports",
    ])
    with tabs[0]:
        render_overview()
    with tabs[1]:
        render_swaps()
    with tabs[2]:
        render_trades()
    with tabs[3]:
        render_latency_and_copy()
    with tabs[4]:
        render_entry_context()
    with tabs[5]:
        render_reports()


if __name__ == "__main__":
    main()

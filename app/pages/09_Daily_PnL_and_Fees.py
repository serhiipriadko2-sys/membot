from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "processed"
REPORTS_DIR = ROOT / "reports"

DAILY_PATH = DATA_DIR / "daily_pnl_calendar.csv"
DAILY_REPORT = REPORTS_DIR / "daily_pnl_calendar_report.md"
FEE_PATH = DATA_DIR / "priority_fee_jito_audit.csv"
FEE_REPORT = REPORTS_DIR / "priority_fee_jito_audit_report.md"

st.set_page_config(
    page_title="Daily PnL / Fees — membot",
    page_icon="📆",
    layout="wide",
)


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception as exc:
        return pd.DataFrame({"_load_error": [str(exc)]})


def num(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(df[col], errors="coerce")


def read_md(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def render_guardrails() -> None:
    st.warning(
        "Эта страница проверяет dashboard claims через raw-replay артефакты. "
        "NO_MEV_EVIDENCE не доказывает отсутствие приватного роутинга; Jito bundle inclusion требует отдельного bundle/block-engine trace."
    )
    with st.expander("Guardrails", expanded=False):
        st.markdown(
            """
            - `daily_pnl_calendar.csv` строится по `trades_paired.csv`, группировка по `exit_time` UTC.
            - Если `fees_sol` пустой, net PnL может совпадать с gross PnL.
            - `priority_fee_jito_audit.csv` ищет ComputeBudget и on-chain tip-transfer candidates.
            - Jito/private bundle нельзя доказать обычным `getTransaction` payload без внешнего bundle trace.
            - Dashboard green-days / MEV labels считаются PARTIAL, пока не совпали с raw artefacts.
            """
        )


def render_daily(df: pd.DataFrame) -> None:
    st.subheader("📆 Daily PnL calendar")
    if df.empty:
        st.info("`data/processed/daily_pnl_calendar.csv` пока не найден. Запусти `python scripts/31_build_daily_pnl_calendar.py`.")
        return
    if "_load_error" in df.columns:
        st.error(df["_load_error"].iloc[0])
        return

    net = num(df, "net_pnl_sol")
    green = df.get("is_green_day", pd.Series(dtype=str)).astype(str).str.lower().eq("true")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Days", len(df))
    c2.metric("Green days", int(green.sum()))
    c3.metric("Net PnL SOL", f"{net.sum():.4f}" if not net.empty else "—")
    c4.metric("Red/flat days", int((~green).sum()) if len(green) else 0)

    chart_df = df.copy()
    if "date_utc" in chart_df.columns and "net_pnl_sol" in chart_df.columns:
        chart_df["net_pnl_sol"] = pd.to_numeric(chart_df["net_pnl_sol"], errors="coerce")
        st.bar_chart(chart_df.set_index("date_utc")[["net_pnl_sol"]])
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_fee(df: pd.DataFrame) -> None:
    st.subheader("⛽ Priority fee / Jito audit")
    if df.empty:
        st.info("`data/processed/priority_fee_jito_audit.csv` пока не найден. Запусти `python scripts/32_audit_priority_fees_and_jito.py`.")
        return
    if "_load_error" in df.columns:
        st.error(df["_load_error"].iloc[0])
        return

    verdicts = df.get("verdict", pd.Series(dtype=str)).astype(str)
    has_jito = df.get("has_jito_tip", pd.Series(dtype=str)).astype(str).str.lower().eq("true")
    has_cb = df.get("has_compute_budget_ix", pd.Series(dtype=str)).astype(str).str.lower().eq("true")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Transactions", len(df))
    c2.metric("ComputeBudget ix", int(has_cb.sum()))
    c3.metric("Jito tip candidates", int(has_jito.sum()))
    c4.metric("Verdict types", int(verdicts.nunique()))

    st.bar_chart(verdicts.value_counts())
    if "fee_bucket" in df.columns:
        st.bar_chart(df["fee_bucket"].astype(str).value_counts())
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_reports() -> None:
    st.subheader("📄 Reports")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Daily PnL report")
        text = read_md(DAILY_REPORT)
        st.markdown(text if text else "`reports/daily_pnl_calendar_report.md` пока не найден.")
    with col2:
        st.markdown("#### Priority/Jito audit report")
        text = read_md(FEE_REPORT)
        st.markdown(text if text else "`reports/priority_fee_jito_audit_report.md` пока не найден.")


def main() -> None:
    st.title("📆 Daily PnL / Fees")
    st.caption("Raw-replay проверка PnL-calendar, priority fees и Jito-tip candidates.")
    render_guardrails()

    st.code(
        "python scripts/31_build_daily_pnl_calendar.py\n"
        "python scripts/32_audit_priority_fees_and_jito.py",
        language="bash",
    )

    daily_df = load_csv(DAILY_PATH)
    fee_df = load_csv(FEE_PATH)
    tab1, tab2, tab3 = st.tabs(["Daily PnL", "Priority/Jito", "Reports"])
    with tab1:
        render_daily(daily_df)
    with tab2:
        render_fee(fee_df)
    with tab3:
        render_reports()


if __name__ == "__main__":
    main()

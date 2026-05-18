from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "processed"
REPORTS_DIR = ROOT / "reports"

TESTS_PATH = DATA_DIR / "entry_exit_hypothesis_tests.csv"
REPORT_PATH = REPORTS_DIR / "entry_exit_hypothesis_report.md"
CONFIG_PATH = ROOT / "configs" / "entry_exit_hypotheses.v0.yaml"

st.set_page_config(
    page_title="Entry/Exit Hypotheses — membot",
    page_icon="🧪",
    layout="wide",
)


def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception as exc:
        return pd.DataFrame({"_load_error": [str(exc)]})


def numeric(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(df[col], errors="coerce")


def render_guardrails() -> None:
    st.warning(
        "PASS_HYP / PARTIAL_HYP — это поддержка гипотезы на текущих CSV, а не факт и не торговый сигнал. "
        "UNKNOWN означает, что нужных колонок ещё нет."
    )
    with st.expander("Guardrails", expanded=False):
        st.markdown(
            """
            - `HYP_THRESHOLD` = порог не откалиброван на OOS.
            - `RAW_REQUIRED` = нужен raw/lifecycle/liquidity слой.
            - `SYNTHETIC` строки нельзя использовать для wallet-specific claims.
            - Для trailing-stop нужен intra-trade price path.
            - Для entry-гипотез нужны `token_lifecycle_context.csv` и `liquidity_context.csv`.
            """
        )


def render_summary(df: pd.DataFrame) -> None:
    verdict_col = "verdict" if "verdict" in df.columns else None
    if not verdict_col:
        st.info("В CSV нет колонки `verdict`.")
        return
    verdicts = df[verdict_col].astype(str).str.upper()
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("PASS_HYP", int((verdicts == "PASS_HYP").sum()))
    c2.metric("PARTIAL_HYP", int((verdicts == "PARTIAL_HYP").sum()))
    c3.metric("NO_SUPPORT", int((verdicts == "NO_SUPPORT").sum()))
    c4.metric("UNKNOWN", int((verdicts == "UNKNOWN").sum()))
    c5.metric("Всего", len(df))

    synth_col = "synthetic_suspect_rows"
    if synth_col in df.columns:
        synth_total = int(numeric(df, synth_col).fillna(0).sum())
        if synth_total:
            st.error(f"Обнаружены synthetic-looking rows: {synth_total}. Такой run нельзя использовать для claims.")
        else:
            st.success("Synthetic-looking rows не обнаружены в текущем отчёте.")


def render_charts(df: pd.DataFrame) -> None:
    verdict_col = "verdict" if "verdict" in df.columns else None
    scope_col = "scope" if "scope" in df.columns else None
    rate_col = "support_rate_pct" if "support_rate_pct" in df.columns else None

    if verdict_col:
        st.bar_chart(df[verdict_col].astype(str).value_counts())
    if scope_col and verdict_col:
        pivot = pd.crosstab(df[scope_col].astype(str), df[verdict_col].astype(str))
        st.dataframe(pivot, use_container_width=True)
    if rate_col:
        plot_df = df.copy()
        plot_df[rate_col] = pd.to_numeric(plot_df[rate_col], errors="coerce")
        chart_df = plot_df.dropna(subset=[rate_col]).set_index("hypothesis_id")[[rate_col]] if "hypothesis_id" in plot_df.columns else plot_df[[rate_col]]
        if not chart_df.empty:
            st.bar_chart(chart_df)


def render_tables(df: pd.DataFrame) -> None:
    verdict_col = "verdict" if "verdict" in df.columns else None
    if verdict_col:
        supported = df[df[verdict_col].astype(str).str.upper().isin(["PASS_HYP", "PARTIAL_HYP"])]
        unknown = df[df[verdict_col].astype(str).str.upper().eq("UNKNOWN")]
        with st.expander("Поддержанные гипотезы", expanded=True):
            st.dataframe(supported, use_container_width=True, hide_index=True)
        with st.expander("UNKNOWN / missing data", expanded=True):
            st.dataframe(unknown, use_container_width=True, hide_index=True)
    with st.expander("Полная таблица", expanded=False):
        st.dataframe(df, use_container_width=True, hide_index=True)


def render_report() -> None:
    st.subheader("📄 Отчёт")
    if REPORT_PATH.exists():
        st.markdown(REPORT_PATH.read_text(encoding="utf-8", errors="replace"))
    else:
        st.info("`reports/entry_exit_hypothesis_report.md` пока не найден. Запусти `python scripts/30_test_entry_exit_hypotheses.py`.")


def main() -> None:
    st.title("🧪 Entry/Exit Hypotheses")
    st.caption("Проверка гипотез входа/выхода: HYP_THRESHOLD / RAW_REQUIRED / UNKNOWN-first.")
    render_guardrails()

    st.markdown("### Пути")
    st.code(
        f"config: {CONFIG_PATH.relative_to(ROOT)}\n"
        f"tests:  {TESTS_PATH.relative_to(ROOT)}\n"
        f"report: {REPORT_PATH.relative_to(ROOT)}\n"
        "run:    python scripts/30_test_entry_exit_hypotheses.py",
        language="text",
    )

    df = load_csv(TESTS_PATH)
    if df.empty:
        st.info("`entry_exit_hypothesis_tests.csv` пока не найден или пустой.")
        st.markdown(
            """
            Минимальный запуск:
            ```bash
            python scripts/30_test_entry_exit_hypotheses.py
            ```
            Если большинство entry-гипотез вернёт `UNKNOWN`, это ожидаемо: нужны lifecycle/liquidity/security колонки.
            """
        )
        render_report()
        return

    render_summary(df)
    render_charts(df)
    render_tables(df)
    render_report()


if __name__ == "__main__":
    main()

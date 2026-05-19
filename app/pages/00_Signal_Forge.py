from __future__ import annotations

import hashlib
import io
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

try:
    import plotly.express as px
except Exception:  # pragma: no cover
    px = None

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "processed"
REPORTS_DIR = ROOT / "reports"

DATASETS = {
    "wallet_swaps": DATA_DIR / "wallet_swaps.csv",
    "trades_paired": DATA_DIR / "trades_paired.csv",
    "daily_pnl_calendar": DATA_DIR / "daily_pnl_calendar.csv",
    "priority_fee_jito_audit": DATA_DIR / "priority_fee_jito_audit.csv",
    "entry_exit_hypothesis_tests": DATA_DIR / "entry_exit_hypothesis_tests.csv",
    "trigger_tests": DATA_DIR / "trigger_tests.csv",
    "entry_context": DATA_DIR / "entry_context.csv",
    "control_points": DATA_DIR / "control_points.csv",
    "latency_sim": DATA_DIR / "latency_sim.csv",
    "copy_stress_model": DATA_DIR / "copy_stress_model.csv",
}

LABELS = {
    "wallet_swaps": "Raw swaps",
    "trades_paired": "FIFO trades",
    "daily_pnl_calendar": "Daily PnL",
    "priority_fee_jito_audit": "Fee/Jito audit",
    "entry_exit_hypothesis_tests": "Entry/exit hypotheses",
    "trigger_tests": "Pre-buy triggers",
    "entry_context": "Entry context",
    "control_points": "Control points",
    "latency_sim": "Latency sim",
    "copy_stress_model": "Copy stress",
    "daily_pnl_calendar_report": "Daily PnL report",
    "priority_fee_jito_audit_report": "Fee/Jito report",
    "entry_exit_hypothesis_report": "Entry/exit report",
    "other": "Other",
}

CRITICAL = ["wallet_swaps", "trades_paired", "daily_pnl_calendar", "priority_fee_jito_audit"]
REPORT_TYPES = ["daily_pnl_calendar_report", "priority_fee_jito_audit_report", "entry_exit_hypothesis_report", "other"]
KNOWN_TYPES = [*DATASETS.keys(), *REPORT_TYPES]

st.set_page_config(page_title="Signal Forge — membot", page_icon="🜂", layout="wide")


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {--bg:#050814;--panel:rgba(15,23,42,.74);--line:rgba(148,163,184,.22);--cyan:#22d3ee;--green:#34d399;--amber:#f59e0b;--red:#fb7185;--muted:#91a4bb;}
        html, body, [data-testid="stAppViewContainer"] {background:radial-gradient(circle at 10% 0%,rgba(34,211,238,.16),transparent 28%),radial-gradient(circle at 92% 8%,rgba(167,139,250,.16),transparent 22%),linear-gradient(180deg,#050814,#07111f 50%,#050814);}
        [data-testid="stHeader"] {background:rgba(5,8,20,.58);backdrop-filter:blur(10px)}
        [data-testid="stSidebar"] {background:linear-gradient(180deg,rgba(3,7,18,.98),rgba(8,13,28,.96));border-right:1px solid var(--line)}
        .block-container {padding-top:1rem;max-width:1440px}.stTabs [data-baseweb="tab-list"]{gap:8px;flex-wrap:wrap}.stTabs [data-baseweb="tab"]{border:1px solid var(--line);border-radius:999px;background:rgba(15,23,42,.48);padding:8px 14px}.stTabs [aria-selected="true"]{border-color:rgba(34,211,238,.55);background:rgba(34,211,238,.10)}
        [data-testid="stMetric"]{background:linear-gradient(180deg,rgba(15,23,42,.86),rgba(8,13,28,.78));border:1px solid var(--line);border-radius:18px;padding:14px 16px;box-shadow:0 18px 42px rgba(0,0,0,.24)}
        .sf-hero{position:relative;overflow:hidden;border:1px solid rgba(34,211,238,.28);border-radius:28px;padding:24px 26px;margin-bottom:18px;background:linear-gradient(120deg,rgba(8,13,28,.96),rgba(12,22,42,.88));box-shadow:0 24px 70px rgba(0,0,0,.34)}
        .sf-hero:before{content:"";position:absolute;inset:0;background-image:linear-gradient(rgba(148,163,184,.07) 1px,transparent 1px),linear-gradient(90deg,rgba(148,163,184,.06) 1px,transparent 1px);background-size:42px 42px;mask-image:linear-gradient(90deg,black,transparent 80%);pointer-events:none}.sf-hero>*{position:relative;z-index:1}
        .sf-kicker{color:var(--cyan);letter-spacing:.18em;text-transform:uppercase;font-size:.72rem;font-weight:800}.sf-hero h1{margin:.25rem 0 .35rem;font-size:clamp(2rem,4vw,3.2rem);line-height:.98}.sf-hero p{max-width:880px;color:#b9c8dc;margin:.35rem 0 0}.sf-badges{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}.sf-badge{border:1px solid rgba(148,163,184,.28);border-radius:999px;padding:7px 11px;background:rgba(15,23,42,.7);font-size:.78rem}.ok{color:var(--green)}.warn{color:var(--amber)}.bad{color:var(--red)}.cyan{color:var(--cyan)}.muted{color:var(--muted)}
        .sf-panel,.sf-card,.sf-empty{border:1px solid var(--line);border-radius:22px;background:linear-gradient(180deg,rgba(15,23,42,.74),rgba(8,13,28,.68));box-shadow:0 16px 42px rgba(0,0,0,.20)}.sf-panel{padding:18px 20px;margin-bottom:16px}.sf-card{padding:15px 16px;height:100%}.sf-card h3{margin:0 0 6px}.sf-small{font-size:.78rem;color:var(--muted)}.sf-empty{padding:18px 20px;border-style:dashed;border-color:rgba(245,158,11,.36)}
        .sf-ladder{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:12px}.sf-ladder div{padding:10px 12px;border-radius:16px;background:rgba(15,23,42,.72);border:1px solid var(--line)}.sf-ladder strong{display:block}.sf-ladder span{color:var(--muted);font-size:.76rem}
        @media(max-width:760px){.block-container{padding-left:.8rem;padding-right:.8rem}.sf-hero{padding:18px 16px;border-radius:22px}.sf-ladder{grid-template-columns:1fr}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def h(body: str) -> None:
    st.markdown(body, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_csv(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(p)
    except Exception as exc:
        return pd.DataFrame({"_load_error": [str(exc)]})


def uploaded() -> dict[str, dict[str, Any]]:
    return st.session_state.get("sf_uploaded", {})


def infer_type(file_name: str) -> str:
    name = Path(file_name).stem.lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "daily_pnl_calendar_report": "daily_pnl_calendar_report",
        "priority_fee_jito_audit_report": "priority_fee_jito_audit_report",
        "entry_exit_hypothesis_report": "entry_exit_hypothesis_report",
        "daily_pnl_calendar": "daily_pnl_calendar",
        "priority_fee_jito_audit": "priority_fee_jito_audit",
        "entry_exit_hypothesis_tests": "entry_exit_hypothesis_tests",
        "wallet_swaps": "wallet_swaps",
        "trades_paired": "trades_paired",
    }
    for needle, artifact_type in aliases.items():
        if needle in name:
            return artifact_type
    for artifact_type in KNOWN_TYPES:
        if artifact_type in name and artifact_type != "other":
            return artifact_type
    return "other"


def content_format(file_name: str) -> str:
    suffix = Path(file_name).suffix.lower()
    if suffix == ".csv":
        return "csv"
    if suffix in {".md", ".markdown"}:
        return "markdown"
    if suffix == ".json":
        return "json"
    return "text"


def df_from_text(text: str) -> pd.DataFrame:
    try:
        return pd.read_csv(io.StringIO(text))
    except Exception as exc:
        return pd.DataFrame({"_load_error": [str(exc)]})


def local_df(name: str) -> pd.DataFrame:
    if name in uploaded() and uploaded()[name].get("format") == "csv":
        return df_from_text(str(uploaded()[name].get("text") or ""))
    return load_csv(str(DATASETS[name])) if name in DATASETS else pd.DataFrame()


def status_df() -> pd.DataFrame:
    rows = []
    for name, path in DATASETS.items():
        up = uploaded().get(name)
        exists = bool(up) or path.exists()
        if up:
            rows.append({"Артефакт": LABELS[name], "Код": name, "Есть": True, "Файл": up.get("file"), "Строк": up.get("rows", 0), "Байт": up.get("bytes", 0), "Источник": "upload"})
        else:
            rows.append({"Артефакт": LABELS[name], "Код": name, "Есть": exists, "Файл": str(path.relative_to(ROOT)), "Строк": len(load_csv(str(path))) if exists else 0, "Байт": path.stat().st_size if exists else 0, "Источник": "local"})
    return pd.DataFrame(rows)


def find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def num(df: pd.DataFrame, col: str | None) -> pd.Series:
    if not col or col not in df.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(df[col], errors="coerce")


def pnl_col(df: pd.DataFrame) -> str | None:
    return find_col(df, ["net_pnl_sol", "pnl_sol", "gross_pnl_sol", "net_pnl_usd", "copy_net_pnl_usd"])


def metric_number(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):,.4f}".rstrip("0").rstrip(".")


def empty(title: str, body: str, command: str | None = None) -> None:
    cmd = f"<code>{command}</code>" if command else ""
    h(f"<div class='sf-empty'><h3>{title}</h3><p class='muted'>{body}</p>{cmd}</div>")


def table(df: pd.DataFrame, key: str, rows: int = 500) -> None:
    if df.empty:
        return
    q = st.text_input("Фильтр", key=f"sf_filter_{key}", placeholder="mint, signature, verdict, token...")
    view = df
    if q:
        mask = pd.Series(False, index=df.index)
        for col in df.columns:
            mask = mask | df[col].astype(str).str.contains(q, case=False, na=False)
        view = df[mask]
    st.dataframe(view.head(rows), use_container_width=True, hide_index=True)


def hero() -> None:
    h(
        """
        <div class="sf-hero">
          <div class="sf-kicker">SOLANA WALLET FORENSICS · SIGNAL FORGE</div>
          <h1>membot: raw truth before copy</h1>
          <p>Особый интерфейс reverse-engineering кошелька: сначала raw artefacts, FIFO, fees/Jito и controls; только потом гипотезы pre-buy триггеров.</p>
          <div class="sf-badges">
            <span class="sf-badge ok">🜂 Read-only</span>
            <span class="sf-badge">Target wallet locked</span>
            <span class="sf-badge warn">Dashboard ≠ raw truth</span>
            <span class="sf-badge">Upload-first mobile flow</span>
          </div>
        </div>
        """
    )


def truth_ladder() -> None:
    h(
        """
        <div class="sf-panel">
          <div class="sf-small">TRUTH LADDER</div>
          <div class="sf-ladder">
            <div><strong>RAW</strong><span>signatures / transactions / CSV</span></div>
            <div><strong>REPLAY</strong><span>FIFO / fees / controls</span></div>
            <div><strong>HYP</strong><span>models / trigger candidates</span></div>
            <div><strong>DASHBOARD</strong><span>витрина, не SoT</span></div>
          </div>
        </div>
        """
    )


def command_center() -> None:
    status = status_df()
    found = int(status["Есть"].sum())
    expected = len(status)
    critical_found = int(status[status["Код"].isin(CRITICAL)]["Есть"].sum())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Artifacts", f"{found}/{expected}")
    c2.metric("Critical raw", f"{critical_found}/{len(CRITICAL)}")
    c3.metric("Rows", int(status["Строк"].sum()))
    c4.metric("Coverage", f"{found / max(expected, 1):.0%}")
    if critical_found < len(CRITICAL):
        empty("Raw chain incomplete", "Для forensic verdict нужны Raw swaps, FIFO trades, Daily PnL и Fee/Jito. Пока один якорь отсутствует — держим UNKNOWN.", "GitHub Actions → Run forensic verification → limit=600 → upload artifact")
    truth_ladder()
    st.markdown("### Data deck")
    st.dataframe(status, use_container_width=True, hide_index=True)
    cols = st.columns(5)
    cards = [
        ("Raw replay", "wallet_swaps", "signatures → swaps"),
        ("FIFO", "trades_paired", "paired trades / PnL"),
        ("Green days", "daily_pnl_calendar", "raw daily calendar"),
        ("Fee/Jito", "priority_fee_jito_audit", "ComputeBudget / tips"),
        ("Triggers", "trigger_tests", "PASS/PARTIAL/UNKNOWN"),
    ]
    for col, (title, code, desc) in zip(cols, cards):
        ok = bool(status.loc[status["Код"].eq(code), "Есть"].any())
        state = "ok" if ok else "warn"
        col.markdown(f"<div class='sf-card'><div class='sf-small'>NODE</div><h3>{title}</h3><div class='{state}'>{desc}</div></div>", unsafe_allow_html=True)


def raw_swaps() -> None:
    df = local_df("wallet_swaps")
    st.markdown("### Raw swaps")
    st.caption("Chain of custody начинается здесь: нормализованные swap rows.")
    if df.empty:
        empty("Raw swaps отсутствуют", "Загрузи `wallet_swaps.csv` или запусти pipeline.")
        return
    side = find_col(df, ["side", "swap_side"])
    mint = find_col(df, ["token_mint", "mint"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", len(df))
    c2.metric("Unique mint", df[mint].nunique() if mint else "—")
    c3.metric("FAILED", int((df[side].astype(str).str.upper() == "FAILED").sum()) if side else "—")
    c4.metric("UNKNOWN", int((df[side].astype(str).str.upper() == "UNKNOWN").sum()) if side else "—")
    if side and px:
        st.plotly_chart(px.histogram(df, x=side, title="BUY / SELL / FAILED"), use_container_width=True)
    table(df, "swaps")


def fifo() -> None:
    df = local_df("trades_paired")
    st.markdown("### FIFO trades")
    st.caption("PnL и hold time из paired trades, не из внешней витрины.")
    if df.empty:
        empty("FIFO trades отсутствуют", "Загрузи `trades_paired.csv` или запусти `scripts/04_pair_trades.py`.")
        return
    pcol = pnl_col(df)
    pnl = num(df, pcol)
    hold = find_col(df, ["hold_seconds", "holding_seconds"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Trades", len(df))
    c2.metric("PnL", metric_number(float(pnl.sum())) if not pnl.empty else "—")
    c3.metric("Win rate", f"{(pnl > 0).sum() / max(1, pnl.notna().sum()):.1%}" if not pnl.empty else "—")
    c4.metric("Profit factor", metric_number(float(pnl[pnl > 0].sum() / abs(pnl[pnl < 0].sum()))) if not pnl.empty and (pnl < 0).any() else "—")
    if pcol and px:
        st.plotly_chart(px.histogram(df, x=pcol, nbins=80, title="PnL distribution"), use_container_width=True)
    if hold and px:
        st.plotly_chart(px.histogram(df, x=hold, nbins=80, title="Hold time"), use_container_width=True)
    table(df, "fifo")


def daily_pnl() -> None:
    df = local_df("daily_pnl_calendar")
    st.markdown("### Daily PnL calendar")
    st.caption("Green-days сверяются raw replay календарём.")
    if df.empty:
        empty("Daily PnL отсутствует", "Нужен `daily_pnl_calendar.csv` из forensic verification artifact.", "python scripts/31_build_daily_pnl_calendar.py")
        return
    net_col = find_col(df, ["net_pnl_sol", "gross_pnl_sol", "pnl_sol"])
    green_col = find_col(df, ["is_green_day"])
    net = num(df, net_col)
    green = df[green_col].astype(str).str.lower().eq("true") if green_col else pd.Series(dtype=bool)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Days", len(df))
    c2.metric("Green", int(green.sum()) if green_col else "—")
    c3.metric("Red/flat", int((~green).sum()) if green_col else "—")
    c4.metric("Net SOL", metric_number(float(net.sum())) if not net.empty else "—")
    if net_col and "date_utc" in df.columns and px:
        plot = df.copy(); plot[net_col] = pd.to_numeric(plot[net_col], errors="coerce")
        st.plotly_chart(px.bar(plot, x="date_utc", y=net_col, title="Daily realized PnL"), use_container_width=True)
    table(df, "daily")


def fee_jito() -> None:
    df = local_df("priority_fee_jito_audit")
    st.markdown("### Priority fee / Jito audit")
    st.caption("NO_MEV_EVIDENCE не доказывает отсутствие private routing.")
    if df.empty:
        empty("Fee/Jito audit отсутствует", "Нужен `priority_fee_jito_audit.csv`.", "python scripts/32_audit_priority_fees_and_jito.py")
        return
    verdict = find_col(df, ["verdict"])
    has_jito = df.get("has_jito_tip", pd.Series(dtype=str)).astype(str).str.lower().eq("true")
    has_cb = df.get("has_compute_budget_ix", pd.Series(dtype=str)).astype(str).str.lower().eq("true")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Transactions", len(df))
    c2.metric("ComputeBudget", int(has_cb.sum()))
    c3.metric("Jito tips", int(has_jito.sum()))
    c4.metric("Verdicts", int(df[verdict].nunique()) if verdict else "—")
    if verdict and px:
        st.plotly_chart(px.histogram(df, x=verdict, title="Evidence verdicts"), use_container_width=True)
    if "fee_bucket" in df.columns and px:
        st.plotly_chart(px.histogram(df, x="fee_bucket", title="Fee buckets"), use_container_width=True)
    table(df, "fee")


def triggers() -> None:
    df = local_df("trigger_tests")
    alt = local_df("entry_exit_hypothesis_tests")
    if df.empty and not alt.empty:
        df = alt
    st.markdown("### Pre-buy triggers")
    st.caption("PASS/PARTIAL/UNKNOWN — поддержка гипотезы, не торговый сигнал.")
    if df.empty:
        empty("Trigger tests отсутствуют", "Нужны trigger tests или entry_exit_hypothesis_tests.", "python scripts/30_test_entry_exit_hypotheses.py")
        return
    status = find_col(df, ["status", "verdict"])
    family = find_col(df, ["family", "scope"])
    statuses = df[status].astype(str).str.upper() if status else pd.Series(dtype=str)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("PASS", int(statuses.isin(["PASS", "PASS_HYP"]).sum()) if status else 0)
    c2.metric("PARTIAL", int(statuses.isin(["PARTIAL", "PARTIAL_HYP"]).sum()) if status else 0)
    c3.metric("UNKNOWN", int((statuses == "UNKNOWN").sum()) if status else 0)
    c4.metric("FAIL", int(statuses.isin(["FAIL", "NO_SIGNAL", "NO_SUPPORT"]).sum()) if status else 0)
    if status and px:
        st.plotly_chart(px.histogram(df, x=status, title="Trigger verdicts"), use_container_width=True)
    if family and status and px:
        st.plotly_chart(px.histogram(df, x=family, color=status, title="Families / scopes"), use_container_width=True)
    with st.expander("Guardrails", expanded=False):
        st.markdown("- `PASS` = поддержка на текущем sample.\n- `UNKNOWN` = данных мало.\n- Никакой статус не создаёт BUY без OOS.")
    table(df, "triggers")


def upload() -> None:
    st.markdown("### Upload run artifacts")
    files = st.file_uploader("CSV / MD / JSON / TXT", type=["csv", "md", "markdown", "json", "txt"], accept_multiple_files=True)
    parsed = {}
    if not files and not uploaded():
        empty("Файлы ещё не загружены", "Скачай GitHub Actions artifact и загрузи нужные CSV/MD сюда.")
        return
    for file in files or []:
        data = file.getvalue()
        text = data.decode("utf-8", errors="replace")
        fmt = content_format(file.name)
        auto = infer_type(file.name)
        selected = st.selectbox(f"Тип: {file.name}", KNOWN_TYPES, index=KNOWN_TYPES.index(auto), key=f"type_{file.name}_{hashlib.sha256(data).hexdigest()[:8]}", format_func=lambda x: LABELS.get(x, x))
        rows = len(df_from_text(text)) if fmt == "csv" else 0
        parsed[selected] = {"file": file.name, "format": fmt, "rows": rows, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "text": text}
        with st.expander(f"Preview: {file.name}", expanded=False):
            if fmt == "csv":
                st.dataframe(df_from_text(text).head(50), use_container_width=True, hide_index=True)
            elif fmt == "markdown":
                st.markdown(text[:8000])
            else:
                st.code(text[:8000])
    if parsed:
        st.session_state["sf_uploaded"] = parsed
    if uploaded():
        st.markdown("#### Artifact map")
        st.dataframe(pd.DataFrame([{"Тип": LABELS.get(k, k), "Код": k, "Файл": v.get("file"), "Строк": v.get("rows"), "Байт": v.get("bytes"), "SHA256": v.get("sha256")} for k, v in uploaded().items()]), use_container_width=True, hide_index=True)


def reports() -> None:
    st.markdown("### Reports")
    md = {k: str(v.get("text") or "") for k, v in uploaded().items() if v.get("format") in {"markdown", "text"}}
    if md:
        key = st.selectbox("Uploaded report", sorted(md), format_func=lambda x: LABELS.get(x, x))
        st.markdown(md[key])
        return
    if not REPORTS_DIR.exists():
        empty("Reports folder отсутствует", "Нет локальной папки `reports/`.")
        return
    paths = sorted(REPORTS_DIR.glob("*.md"))
    if not paths:
        empty("Markdown отчёты не найдены", "Загрузи `.md` из artifact или запусти report builders.")
        return
    selected = st.selectbox("Report", [str(p.relative_to(ROOT)) for p in paths])
    st.markdown((ROOT / selected).read_text(encoding="utf-8", errors="replace"))


def main() -> None:
    inject_css()
    hero()
    tabs = st.tabs(["⌁ Command", "Raw", "FIFO", "Daily PnL", "Fee/Jito", "Triggers", "Reports", "Upload"])
    with tabs[0]: command_center()
    with tabs[1]: raw_swaps()
    with tabs[2]: fifo()
    with tabs[3]: daily_pnl()
    with tabs[4]: fee_jito()
    with tabs[5]: triggers()
    with tabs[6]: reports()
    with tabs[7]: upload()


if __name__ == "__main__":
    main()

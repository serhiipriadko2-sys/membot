from __future__ import annotations

import hashlib
import io
import math
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "processed"
REPORTS_DIR = ROOT / "reports"
TARGET_WALLET = "7BNaxx6KdUYrjACNQZ9He26NBFoFxujQMAfNLnArLGH5"

DATASETS = {
    "wallet_swaps": DATA_DIR / "wallet_swaps.csv",
    "trades_paired": DATA_DIR / "trades_paired.csv",
    "daily_pnl_calendar": DATA_DIR / "daily_pnl_calendar.csv",
    "priority_fee_jito_audit": DATA_DIR / "priority_fee_jito_audit.csv",
    "trigger_tests": DATA_DIR / "trigger_tests.csv",
    "entry_exit_hypothesis_tests": DATA_DIR / "entry_exit_hypothesis_tests.csv",
    "entry_context": DATA_DIR / "entry_context.csv",
    "control_points": DATA_DIR / "control_points.csv",
}
CRITICAL = ["wallet_swaps", "trades_paired", "daily_pnl_calendar", "priority_fee_jito_audit"]
LABELS = {
    "wallet_swaps": "Raw swaps",
    "trades_paired": "FIFO trades",
    "daily_pnl_calendar": "Daily PnL",
    "priority_fee_jito_audit": "Fee/Jito audit",
    "trigger_tests": "Pre-buy triggers",
    "entry_exit_hypothesis_tests": "Entry/exit hypotheses",
    "entry_context": "Entry context",
    "control_points": "Control points",
    "other": "Other",
}
KNOWN_TYPES = [*DATASETS.keys(), "daily_pnl_calendar_report", "priority_fee_jito_audit_report", "entry_exit_hypothesis_report", "other"]

GOLD = "#FFC36B"
EMBER = "#FF6A1A"
VIOLET = "#7A5CFF"
CYAN = "#00E6FF"
MINT = "#00FFC2"
PANEL = "rgba(10,15,26,0.66)"
TEXT = "#F5EFE2"
MUTED = "#9CA8B7"

st.set_page_config(page_title="membot - Iskra Forge", page_icon="*", layout="wide", initial_sidebar_state="expanded")


def inject_css() -> None:
    st.markdown("""
    <style>
    :root{--gold:#FFC36B;--ember:#FF6A1A;--violet:#7A5CFF;--cyan:#00E6FF;--mint:#00FFC2;--ink:#0B0E14;--void:#030407;--panel:rgba(10,15,26,.76);--line:rgba(255,195,107,.22);--muted:#9CA8B7}
    @keyframes pulse{0%,100%{opacity:.55;transform:scale(.96)}50%{opacity:1;transform:scale(1.04)}}
    html,body,[data-testid="stAppViewContainer"]{color:#F5EFE2;background:radial-gradient(circle at 4% 8%,rgba(255,195,107,.14),transparent 22%),radial-gradient(circle at 73% 0%,rgba(0,230,255,.14),transparent 24%),radial-gradient(circle at 92% 22%,rgba(122,92,255,.12),transparent 20%),linear-gradient(180deg,#020305 0%,#070b12 46%,#05070d 100%)}
    [data-testid="stAppViewContainer"]:before{content:"";position:fixed;inset:0;pointer-events:none;background-image:linear-gradient(rgba(255,255,255,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.032) 1px,transparent 1px);background-size:44px 44px;opacity:.58;mask-image:linear-gradient(180deg,black,rgba(0,0,0,.72),transparent 96%)}
    [data-testid="stAppViewContainer"]:after{content:"";position:fixed;left:8vw;right:8vw;top:7.5rem;height:2px;pointer-events:none;background:linear-gradient(90deg,transparent,rgba(255,195,107,.18),var(--gold),rgba(0,230,255,.58),transparent);box-shadow:0 0 18px rgba(255,195,107,.75),0 0 44px rgba(0,230,255,.23);transform:rotate(-2.4deg)}
    [data-testid="stHeader"]{background:rgba(3,4,7,.56);backdrop-filter:blur(12px)}[data-testid="stSidebar"]{background:radial-gradient(circle at 55% 8%,rgba(255,195,107,.12),transparent 34%),linear-gradient(180deg,rgba(2,3,7,.99),rgba(7,10,18,.96));border-right:1px solid rgba(255,195,107,.20)}
    .block-container{padding-top:.85rem;padding-bottom:4rem;max-width:1560px} h1,h2,h3{color:#FFF4D9;letter-spacing:-.02em} code{color:var(--gold);background:rgba(255,195,107,.08);border:1px solid rgba(255,195,107,.14);border-radius:8px;padding:.08rem .35rem}
    .stTabs [data-baseweb="tab-list"]{gap:8px;flex-wrap:wrap;border-bottom:1px solid rgba(255,195,107,.12);padding-bottom:8px}.stTabs [data-baseweb="tab"]{border:1px solid rgba(255,195,107,.18);border-radius:999px;background:rgba(10,15,26,.58);padding:8px 14px;color:#E8DCC7}.stTabs [aria-selected="true"]{border-color:rgba(0,230,255,.52);background:linear-gradient(90deg,rgba(0,230,255,.14),rgba(255,195,107,.10));box-shadow:0 0 24px rgba(0,230,255,.12)}
    [data-testid="stMetric"]{background:linear-gradient(180deg,rgba(13,18,30,.88),rgba(5,8,14,.78));border:1px solid rgba(255,195,107,.18);border-radius:20px;padding:15px 17px;box-shadow:0 18px 44px rgba(0,0,0,.34),inset 0 1px 0 rgba(255,255,255,.04)}[data-testid="stMetricValue"]{color:#F9F2DF}
    .hero{position:relative;overflow:hidden;border:1px solid rgba(255,195,107,.28);border-radius:30px;margin-bottom:18px;background:radial-gradient(circle at 15% 35%,rgba(255,195,107,.18),transparent 26%),radial-gradient(circle at 75% 18%,rgba(0,230,255,.15),transparent 28%),linear-gradient(130deg,rgba(8,12,21,.97),rgba(10,17,30,.90));box-shadow:0 28px 80px rgba(0,0,0,.42),inset 0 1px 0 rgba(255,255,255,.06)}
    .hero:before{content:"";position:absolute;inset:0;background-image:linear-gradient(rgba(255,255,255,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.04) 1px,transparent 1px);background-size:52px 52px;mask-image:linear-gradient(90deg,black,rgba(0,0,0,.72),transparent 92%)}.hero:after{content:"";position:absolute;left:18%;right:5%;top:18%;height:2px;background:linear-gradient(90deg,transparent,rgba(255,195,107,.25),var(--gold),rgba(0,230,255,.55),transparent);box-shadow:0 0 18px rgba(255,195,107,.85);transform:rotate(-6deg)}
    .hero-grid{position:relative;z-index:1;display:grid;grid-template-columns:230px minmax(0,1fr) 330px;gap:18px;padding:22px}.brand{border-right:1px solid rgba(255,195,107,.15);padding:6px 18px 8px 4px;display:flex;flex-direction:column;justify-content:space-between}.logo{display:flex;align-items:center;gap:12px;font-size:1.55rem;font-weight:800;color:#FFE7B4;text-shadow:0 0 22px rgba(255,195,107,.35)}.sigil{width:42px;height:42px;border-radius:14px;display:grid;place-items:center;color:var(--gold);border:1px solid rgba(255,195,107,.34);background:radial-gradient(circle,rgba(255,195,107,.22),rgba(255,195,107,.04));box-shadow:0 0 22px rgba(255,195,107,.28)}
    .ritual{margin:22px auto;width:150px;height:150px;border-radius:50%;border:1px solid rgba(255,195,107,.25);position:relative;background:radial-gradient(circle,rgba(255,195,107,.18),transparent 10%,rgba(255,195,107,.04) 26%,transparent 58%)}.ritual:before{content:"";position:absolute;left:50%;top:-22px;bottom:-22px;width:2px;background:linear-gradient(180deg,transparent,var(--gold),transparent);box-shadow:0 0 16px rgba(255,195,107,.78);transform:translateX(-50%) rotate(7deg)}.ritual:after{content:"*";position:absolute;inset:0;display:grid;place-items:center;font-size:38px;color:var(--gold);text-shadow:0 0 25px rgba(255,195,107,.9);animation:pulse 3.4s ease-in-out infinite}.copy{color:#DDD0B4;line-height:1.45}.tiny{color:#947F5D;font-size:.70rem;letter-spacing:.16em;text-transform:uppercase;margin-top:18px}
    .topbar{display:flex;gap:12px;align-items:center;justify-content:space-between;margin-bottom:14px}.search{flex:1;border:1px solid rgba(148,163,184,.16);background:rgba(2,5,12,.38);border-radius:12px;padding:10px 12px;color:#687386;font-size:.82rem}.cta{border:1px solid rgba(0,230,255,.48);color:#DFFBFF;border-radius:12px;padding:10px 13px;background:rgba(0,230,255,.07);box-shadow:0 0 22px rgba(0,230,255,.12);white-space:nowrap}.kicker{color:var(--gold);letter-spacing:.18em;text-transform:uppercase;font-size:.70rem;font-weight:800}.title{margin:.18rem 0 .28rem;font-size:clamp(2rem,4vw,3.45rem);line-height:.94;color:#FFF4D9}.subtitle{color:#BDC7D4;max-width:820px;margin:.35rem 0 0}
    .badges{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}.chip{border:1px solid rgba(148,163,184,.24);border-radius:999px;padding:7px 11px;background:rgba(11,14,20,.55);font-size:.78rem;color:#E9DECA}.ok{border-color:rgba(0,255,194,.34);color:#9FFFE9}.warn{border-color:rgba(255,195,107,.42);color:#FFD99A}.violet{border-color:rgba(122,92,255,.42);color:#CBBFFF}.hot{border-color:rgba(255,106,26,.42);color:#FFC0A0}
    .kpis{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin:16px 0}.kpi{padding:13px 12px;border:1px solid rgba(255,195,107,.14);border-radius:16px;background:rgba(5,8,14,.54)}.kpi span{display:block;color:#8E9AAD;font-size:.70rem;letter-spacing:.06em;text-transform:uppercase}.kpi strong{display:block;margin-top:4px;color:#F8EED5;font-size:1.12rem}
    .panel,.card,.empty,.signal-card{border:1px solid rgba(255,195,107,.17);border-radius:22px;background:linear-gradient(180deg,rgba(13,18,30,.74),rgba(5,8,14,.70));box-shadow:0 18px 46px rgba(0,0,0,.28),inset 0 1px 0 rgba(255,255,255,.04)}.panel{padding:18px 20px;margin-bottom:16px}.card{padding:15px 16px;height:100%}.small{font-size:.74rem;color:var(--muted);letter-spacing:.12em;text-transform:uppercase}.muted{color:var(--muted)}.empty{padding:18px 20px;border-style:dashed;border-color:rgba(255,195,107,.38)}.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.signal-card{padding:12px 13px;margin-top:10px}.signal-card h4{margin:.1rem 0 .3rem;color:#FFF4D9}.signal-meta{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}.signal-bar{height:6px;background:rgba(255,255,255,.08);border-radius:999px;overflow:hidden;margin-top:10px}.signal-bar i{display:block;height:100%;background:linear-gradient(90deg,var(--cyan),var(--mint),var(--gold));border-radius:999px}.progress{height:5px;border-radius:999px;background:rgba(255,255,255,.08);overflow:hidden;margin-top:8px}.progress i{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,var(--cyan),var(--mint),var(--gold))}.style{display:grid;grid-template-columns:1.35fr 1.45fr 1.1fr 1fr;gap:12px;margin:16px 0 4px}.palette{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap}.swatch{width:54px;height:46px;border-radius:12px;border:1px solid rgba(255,255,255,.12)}.aa{font-size:3.4rem;color:#F3EAD9;line-height:.9}.keywords{display:grid;gap:7px;margin-top:10px;color:#C8D0DC}
    @media(max-width:1100px){.hero-grid,.style{grid-template-columns:1fr}.brand{border-right:0;border-bottom:1px solid rgba(255,195,107,.15)}.kpis{grid-template-columns:repeat(2,1fr)}.cards{grid-template-columns:1fr}}@media(max-width:760px){.block-container{padding-left:.78rem;padding-right:.78rem}.hero-grid{padding:16px}.title{font-size:2.15rem}.kpis{grid-template-columns:1fr}.ritual{width:118px;height:118px}.topbar{flex-direction:column;align-items:stretch}}
    </style>
    """, unsafe_allow_html=True)


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


def df_from_text(text: str) -> pd.DataFrame:
    try:
        return pd.read_csv(io.StringIO(text))
    except Exception as exc:
        return pd.DataFrame({"_load_error": [str(exc)]})


def local_df(name: str) -> pd.DataFrame:
    up = uploaded().get(name)
    if up and up.get("format") == "csv":
        return df_from_text(str(up.get("text") or ""))
    return load_csv(str(DATASETS[name])) if name in DATASETS else pd.DataFrame()


def status_df() -> pd.DataFrame:
    rows = []
    for name, path in DATASETS.items():
        up = uploaded().get(name)
        exists = bool(up) or path.exists()
        rows.append({
            "Artifact": LABELS[name],
            "Code": name,
            "Found": exists,
            "File": up.get("file") if up else str(path.relative_to(ROOT)),
            "Rows": up.get("rows", 0) if up else (len(load_csv(str(path))) if exists else 0),
            "Bytes": up.get("bytes", 0) if up else (path.stat().st_size if exists else 0),
        })
    return pd.DataFrame(rows)


def find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    return next((c for c in candidates if c in df.columns), None)


def numeric_series(df: pd.DataFrame, col: str | None) -> pd.Series:
    if not col or col not in df.columns:
        return pd.Series(dtype="float64")
    return pd.to_numeric(df[col], errors="coerce")


def plotly_layout(fig: go.Figure, height: int = 280) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=34, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, family="Inter, system-ui, sans-serif"),
        hoverlabel=dict(bgcolor="#0B0E14", font_color=TEXT, bordercolor=GOLD),
        legend=dict(orientation="h", y=-0.16, x=0, bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(gridcolor="rgba(255,195,107,0.08)", zeroline=False, color=MUTED)
    fig.update_yaxes(gridcolor="rgba(255,195,107,0.08)", zeroline=False, color=MUTED)
    return fig


def empty(title: str, body: str, command: str | None = None) -> None:
    h(f"<div class='empty'><h3>{title}</h3><p class='muted'>{body}</p>{'<code>'+command+'</code>' if command else ''}</div>")


def table(df: pd.DataFrame, key: str) -> None:
    if df.empty:
        return
    q = st.text_input("Filter", key=f"filter_{key}", placeholder="mint, signature, verdict, token...")
    view = df
    if q:
        mask = pd.Series(False, index=df.index)
        for col in df.columns:
            mask |= df[col].astype(str).str.contains(q, case=False, na=False)
        view = df[mask]
    st.dataframe(view.head(500), use_container_width=True, hide_index=True)


def hero() -> None:
    short = TARGET_WALLET[:7] + "..." + TARGET_WALLET[-5:]
    h(f"""
    <div class='hero'><div class='hero-grid'><aside class='brand'><div><div class='logo'><span class='sigil'>*</span><span>membot</span></div><div class='copy' style='margin-top:18px'>Evidence First.<br/>Hypothesis Always.</div><div class='ritual'></div></div><div class='copy'><div class='tiny'>BUILT FOR TRUTH. NOT HYPE.</div></div></aside><section><div class='topbar'><div class='search'>Search wallet / token / signature... CTRL K</div><div class='cta'>Analyze Wallet *</div></div><div class='kicker'>SIGNAL FORGE - SOLANA MEME INTELLIGENCE</div><div class='title'>raw truth<br/>before copy</div><p class='subtitle'>Forensic interface for wallet reverse-engineering: signatures, FIFO, fee/Jito audit, controls, and pre-buy hypotheses without pretending dashboard claims are raw truth.</p><div class='badges'><span class='chip ok'>Read-only</span><span class='chip violet'>Target {short}</span><span class='chip warn'>Dashboard != SoT</span><span class='chip hot'>No blind copytrade</span></div><div class='kpis'><div class='kpi'><span>Wallet</span><strong>{short}</strong></div><div class='kpi'><span>Mode</span><strong>Forensic</strong></div><div class='kpi'><span>Truth Gate</span><strong>RAW -> HYP</strong></div><div class='kpi'><span>Artifacts</span><strong>Required</strong></div><div class='kpi'><span>Verdict</span><strong>UNKNOWN</strong></div></div></section><aside><div class='panel'><div class='small'>SIGNATURE TRACE</div><p class='muted'>Live cards below are now derived from CSV columns when artifacts are present.</p><div class='badges'><span class='chip ok'>data-driven</span><span class='chip warn'>UNKNOWN on missing raw</span></div></div><div class='panel'><div class='small'>ISKRA KEYWORDS</div><div class='keywords'><span>Evidence First</span><span>Signal Forge</span><span>Mythic Precision</span><span>On-chain Clarity</span></div></div></aside></div></div>
    """)


def build_cluster_figure(swaps: pd.DataFrame, trades: pd.DataFrame) -> go.Figure | None:
    source = swaps if not swaps.empty else trades
    if source.empty:
        return None
    token_col = find_col(source, ["token_mint", "mint", "base_mint", "token_address", "token", "symbol"])
    side_col = find_col(source, ["side", "swap_side", "action", "type"])
    amount_col = find_col(source, ["sol_amount", "amount_sol", "amount_in", "amount_out", "usd_value", "value", "net_pnl_sol", "pnl_sol"])
    if token_col is None:
        return None
    tmp = source.copy()
    tmp["_token"] = tmp[token_col].astype(str).str.slice(0, 12)
    if side_col:
        side = tmp[side_col].astype(str).str.upper()
        tmp["_buy"] = side.str.contains("BUY|IN", regex=True).astype(int)
        tmp["_sell"] = side.str.contains("SELL|OUT", regex=True).astype(int)
    else:
        tmp["_buy"] = 0
        tmp["_sell"] = 0
    if amount_col:
        tmp["_amount"] = pd.to_numeric(tmp[amount_col], errors="coerce").abs().fillna(0)
    else:
        tmp["_amount"] = 1.0
    grouped = tmp.groupby("_token", dropna=False).agg(tx_count=("_token", "size"), buy=("_buy", "sum"), sell=("_sell", "sum"), amount=("_amount", "sum")).reset_index()
    grouped = grouped.sort_values(["tx_count", "amount"], ascending=False).head(18)
    if grouped.empty:
        return None
    max_count = max(float(grouped["tx_count"].max()), 1.0)
    n = len(grouped)
    xs: list[float] = []
    ys: list[float] = []
    for i, count in enumerate(grouped["tx_count"].tolist()):
        angle = (2 * math.pi * i / max(n, 1)) - math.pi / 2
        radius = 1.0 + 0.52 * (float(count) / max_count)
        xs.append(radius * math.cos(angle))
        ys.append(radius * math.sin(angle))
    grouped["x"] = xs
    grouped["y"] = ys
    grouped["balance"] = grouped["buy"] - grouped["sell"]

    fig = go.Figure()
    for _, row in grouped.iterrows():
        fig.add_trace(go.Scatter(x=[0, row["x"]], y=[0, row["y"]], mode="lines", line=dict(color="rgba(0,230,255,0.20)", width=1), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=[0], y=[0], mode="markers+text", marker=dict(size=34, color=GOLD, line=dict(color=CYAN, width=2)), text=["wallet"], textposition="bottom center", name="target wallet", hovertext=[TARGET_WALLET], hoverinfo="text"))
    fig.add_trace(go.Scatter(
        x=grouped["x"], y=grouped["y"], mode="markers+text",
        marker=dict(size=12 + 34 * grouped["tx_count"] / max_count, color=grouped["balance"], colorscale=[[0, EMBER], [0.5, VIOLET], [1, MINT]], showscale=False, line=dict(color="rgba(255,195,107,0.55)", width=1)),
        text=grouped["_token"], textposition="top center", name="tokens",
        hovertemplate="token=%{text}<br>tx=%{customdata[0]}<br>buy=%{customdata[1]}<br>sell=%{customdata[2]}<br>amount=%{customdata[3]:.4f}<extra></extra>",
        customdata=grouped[["tx_count", "buy", "sell", "amount"]].to_numpy(),
    ))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False, scaleanchor="x", scaleratio=1)
    fig.update_layout(title="Cluster map from token interaction frequency", showlegend=False)
    return plotly_layout(fig, height=330)


def build_daily_calendar_figure(daily: pd.DataFrame) -> go.Figure | None:
    if daily.empty:
        return None
    date_col = find_col(daily, ["date_utc", "date", "day", "bucket_date"])
    pnl_col = find_col(daily, ["net_pnl_sol", "pnl_sol", "gross_pnl_sol", "net_pnl_usd", "pnl_usd"])
    if date_col is None or pnl_col is None:
        return None
    df = daily.copy()
    df["_date"] = pd.to_datetime(df[date_col], errors="coerce", utc=True).dt.tz_localize(None)
    df["_pnl"] = pd.to_numeric(df[pnl_col], errors="coerce")
    df = df.dropna(subset=["_date"])
    if df.empty:
        return None
    df["_week"] = df["_date"].dt.to_period("W-MON").dt.start_time.dt.strftime("%Y-%m-%d")
    df["_weekday"] = df["_date"].dt.day_name().str.slice(0, 3)
    weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    pivot = df.pivot_table(index="_weekday", columns="_week", values="_pnl", aggfunc="sum").reindex(weekdays)
    if pivot.empty:
        return None
    fig = go.Figure(data=go.Heatmap(
        z=pivot.to_numpy(), x=list(pivot.columns), y=list(pivot.index),
        colorscale=[[0, EMBER], [0.5, "#1A1F2B"], [1, MINT]], zmid=0,
        colorbar=dict(title=pnl_col, outlinecolor="rgba(255,255,255,0.12)"),
        hovertemplate="week=%{x}<br>day=%{y}<br>pnl=%{z:.4f}<extra></extra>",
    ))
    fig.update_layout(title="Daily PnL calendar from replay artifact")
    return plotly_layout(fig, height=300)


def build_fee_figure(fee: pd.DataFrame) -> go.Figure | None:
    if fee.empty:
        return None
    verdict_col = find_col(fee, ["verdict", "fee_verdict", "evidence_verdict"])
    jito_col = find_col(fee, ["has_jito_tip", "jito_tip", "jito_detected"])
    cb_col = find_col(fee, ["has_compute_budget_ix", "compute_budget", "has_priority_fee"])
    labels: list[str] = []
    values: list[int] = []
    if verdict_col:
        counts = fee[verdict_col].astype(str).fillna("UNKNOWN").value_counts().head(6)
        labels.extend(counts.index.tolist())
        values.extend([int(v) for v in counts.values.tolist()])
    else:
        labels.append("transactions")
        values.append(len(fee))
    if jito_col:
        labels.append("Jito tip rows")
        values.append(int(fee[jito_col].astype(str).str.lower().isin(["true", "1", "yes"]).sum()))
    if cb_col:
        labels.append("ComputeBudget rows")
        values.append(int(fee[cb_col].astype(str).str.lower().isin(["true", "1", "yes"]).sum()))
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.62, marker=dict(colors=[CYAN, GOLD, VIOLET, MINT, EMBER, "#8EA0B8", "#364152"]), textinfo="label+value")])
    fig.update_layout(title="Fee/Jito evidence orbit")
    return plotly_layout(fig, height=300)


def trigger_source_df() -> pd.DataFrame:
    trig = local_df("trigger_tests")
    if not trig.empty:
        return trig
    return local_df("entry_exit_hypothesis_tests")


def score_for_row(row: pd.Series, score_col: str | None, status_col: str | None) -> float:
    if score_col and score_col in row and pd.notna(row[score_col]):
        raw = pd.to_numeric(pd.Series([row[score_col]]), errors="coerce").iloc[0]
        if pd.notna(raw):
            val = float(raw)
            return max(0.0, min(100.0, val * 100 if val <= 1 else val))
    status = str(row.get(status_col, "UNKNOWN") if status_col else "UNKNOWN").upper()
    if "PASS" in status:
        return 92.0
    if "PARTIAL" in status:
        return 58.0
    if "FAIL" in status or "NO_" in status:
        return 12.0
    return 24.0


def build_trigger_radar_figure(triggers: pd.DataFrame) -> go.Figure | None:
    if triggers.empty:
        return None
    name_col = find_col(triggers, ["family", "scope", "trigger", "hypothesis", "feature", "name"])
    status_col = find_col(triggers, ["status", "verdict", "result"])
    score_col = find_col(triggers, ["score", "confidence", "support", "lift", "precision", "win_rate", "value"])
    if name_col is None:
        return None
    df = triggers.copy().head(24)
    df["_score"] = df.apply(lambda row: score_for_row(row, score_col, status_col), axis=1)
    grouped = df.groupby(name_col, dropna=False)["_score"].mean().sort_values(ascending=False).head(8)
    if grouped.empty:
        return None
    fig = go.Figure(data=go.Scatterpolar(r=grouped.values.tolist(), theta=[str(i)[:22] for i in grouped.index.tolist()], fill="toself", line=dict(color=CYAN, width=2), marker=dict(color=GOLD, size=7), name="support"))
    fig.update_layout(title="Trigger radar from hypothesis rows", polar=dict(bgcolor="rgba(0,0,0,0)", radialaxis=dict(range=[0, 100], gridcolor="rgba(255,195,107,0.12)", tickfont=dict(color=MUTED)), angularaxis=dict(gridcolor="rgba(255,195,107,0.10)", tickfont=dict(color=TEXT))), showlegend=False)
    return plotly_layout(fig, height=330)


def render_signal_cards(triggers: pd.DataFrame) -> None:
    if triggers.empty:
        empty("Signal cards need trigger rows", "Upload trigger_tests.csv or entry_exit_hypothesis_tests.csv to convert this panel from decorative to live data.")
        return
    name_col = find_col(triggers, ["trigger", "hypothesis", "feature", "name", "family", "scope"])
    status_col = find_col(triggers, ["status", "verdict", "result"])
    score_col = find_col(triggers, ["score", "confidence", "support", "lift", "precision", "win_rate", "value"])
    note_col = find_col(triggers, ["evidence", "notes", "summary", "description", "reason"])
    df = triggers.copy().head(8)
    df["_score"] = df.apply(lambda row: score_for_row(row, score_col, status_col), axis=1)
    df = df.sort_values("_score", ascending=False).head(5)
    cards = []
    for _, row in df.iterrows():
        name = str(row.get(name_col, "Signal candidate"))[:80] if name_col else "Signal candidate"
        status = str(row.get(status_col, "UNKNOWN"))[:36] if status_col else "UNKNOWN"
        note = str(row.get(note_col, "Needs raw replay and controls."))[:140] if note_col else "Needs raw replay and controls."
        score = float(row["_score"])
        cls = "ok" if score >= 75 else "warn" if score >= 35 else "hot"
        cards.append(f"<div class='signal-card'><div class='small'>LIVE SIGNAL CARD</div><h4>{name}</h4><p class='muted'>{note}</p><div class='signal-meta'><span class='chip {cls}'>{status}</span><span class='chip violet'>score {score:.0f}</span></div><div class='signal-bar'><i style='width:{score:.0f}%'></i></div></div>")
    h("".join(cards))


def render_plot(fig: go.Figure | None, title: str, body: str) -> None:
    if fig is None:
        empty(title, body)
    else:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})


def command_center() -> None:
    status = status_df()
    found = int(status["Found"].sum())
    expected = len(status)
    critical = int(status[status["Code"].isin(CRITICAL)]["Found"].sum())
    coverage = found / max(expected, 1)
    swaps = local_df("wallet_swaps")
    trades = local_df("trades_paired")
    daily = local_df("daily_pnl_calendar")
    fee = local_df("priority_fee_jito_audit")
    triggers = trigger_source_df()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Artifacts", f"{found}/{expected}")
    c2.metric("Critical raw", f"{critical}/{len(CRITICAL)}")
    c3.metric("Rows", int(status["Rows"].sum()))
    c4.metric("Coverage", f"{coverage:.0%}")
    if critical < len(CRITICAL):
        empty("Raw chain incomplete", "Forensic verdict needs Raw swaps, FIFO trades, Daily PnL and Fee/Jito. Missing anchors keep verdict UNKNOWN.", "GitHub Actions -> Run forensic verification -> limit=600 -> upload artifact")

    left, right = st.columns([2.2, 1.0], gap="large")
    with left:
        h(f"""<div class='panel'><div class='small'>WALLET OVERVIEW</div><h3>{TARGET_WALLET[:7]}...{TARGET_WALLET[-5:]}</h3><div class='badges'><span class='chip violet'>Watchlist</span><span class='chip ok'>Read-only</span><span class='chip warn'>Coverage {coverage:.0%}</span></div></div>""")
        chart_cols = st.columns(2)
        with chart_cols[0]:
            render_plot(build_trigger_radar_figure(triggers), "Trigger radar is waiting for data", "Upload trigger tests or entry/exit hypothesis rows.")
        with chart_cols[1]:
            render_plot(build_fee_figure(fee), "Fee/Jito orbit is waiting for data", "Upload priority_fee_jito_audit.csv.")
        render_plot(build_daily_calendar_figure(daily), "Daily calendar is waiting for data", "Upload daily_pnl_calendar.csv to render the heatmap.")
        h(f"""<div class='panel'><div class='small'>RAW ARTIFACT STATUS</div><div class='progress'><i style='width:{critical / max(len(CRITICAL), 1) * 100:.0f}%'></i></div><p class='muted'>{critical}/{len(CRITICAL)} critical artifacts present.</p></div>""")
        st.markdown("### Data deck")
        st.dataframe(status, use_container_width=True, hide_index=True)
    with right:
        h("""<div class='panel'><div class='small'>CLUSTER MAP - TOKEN INTERACTIONS</div>""")
        render_plot(build_cluster_figure(swaps, trades), "Cluster map is waiting for raw swaps", "Upload wallet_swaps.csv or trades_paired.csv to build token interaction graph.")
        h("</div>")
        h("""<div class='panel'><div class='small'>PRE-BUY SIGNAL CARDS</div><p class='muted'>Cards are sorted by available score/status. PASS is support, not a buy command.</p></div>""")
        render_signal_cards(triggers)
    h("""<div class='style'><div class='panel'><div class='small'>SPARK PALETTE</div><div class='palette'><span class='swatch' style='background:#ffc36b'></span><span class='swatch' style='background:#ff6a1a'></span><span class='swatch' style='background:#7a5cff'></span><span class='swatch' style='background:#00e6ff'></span><span class='swatch' style='background:#00ffc2'></span><span class='swatch' style='background:#1a1f2b'></span><span class='swatch' style='background:#0b0e14'></span></div></div><div class='panel'><div class='small'>TYPOGRAPHY</div><div class='aa'>Aa</div><code>0x7A3F...9bK2</code></div><div class='panel'><div class='small'>DATA CHIPS</div><div class='badges'><span class='chip ok'>Confirmed</span><span class='chip warn'>Partial</span><span class='chip hot'>Pending</span><span class='chip violet'>High</span></div></div><div class='panel'><div class='small'>KEYWORDS</div><div class='keywords'><span>Evidence First</span><span>Forensic UI</span><span>Mythic Precision</span><span>Not financial advice</span></div></div></div>""")


def show_dataset(name: str) -> None:
    df = local_df(name)
    st.markdown(f"### {LABELS.get(name, name)}")
    if df.empty:
        empty(f"{LABELS.get(name, name)} missing", "Upload CSV or run the pipeline.")
        return
    c1, c2, c3 = st.columns(3)
    c1.metric("Rows", len(df))
    c2.metric("Columns", len(df.columns))
    c3.metric("Source", "upload/local")
    if name == "daily_pnl_calendar":
        render_plot(build_daily_calendar_figure(df), "Daily calendar unavailable", "Expected date and pnl columns were not found.")
    elif name == "priority_fee_jito_audit":
        render_plot(build_fee_figure(df), "Fee/Jito chart unavailable", "Expected verdict/Jito/ComputeBudget columns were not found.")
    elif name in {"trigger_tests", "entry_exit_hypothesis_tests"}:
        render_plot(build_trigger_radar_figure(df), "Trigger radar unavailable", "Expected trigger/status columns were not found.")
        render_signal_cards(df)
    elif name in {"wallet_swaps", "trades_paired"}:
        render_plot(build_cluster_figure(df, pd.DataFrame()), "Cluster chart unavailable", "Expected token/mint columns were not found.")
    table(df, name)


def upload() -> None:
    st.markdown("### Upload run artifacts")
    files = st.file_uploader("CSV / MD / JSON / TXT", type=["csv", "md", "markdown", "json", "txt"], accept_multiple_files=True)
    parsed: dict[str, dict[str, Any]] = {}
    if not files and not uploaded():
        empty("No files uploaded yet", "Download GitHub Actions artifact and upload CSV/MD files here.")
        return
    for file in files or []:
        data = file.getvalue()
        text = data.decode("utf-8", errors="replace")
        fmt = "csv" if file.name.endswith(".csv") else ("markdown" if file.name.endswith((".md", ".markdown")) else "text")
        auto = next((t for t in KNOWN_TYPES if t != "other" and t in file.name.replace("-", "_")), "other")
        selected = st.selectbox(f"Type: {file.name}", KNOWN_TYPES, index=KNOWN_TYPES.index(auto), key=f"type_{file.name}_{hashlib.sha256(data).hexdigest()[:8]}", format_func=lambda x: LABELS.get(x, x))
        rows = len(df_from_text(text)) if fmt == "csv" else 0
        parsed[selected] = {"file": file.name, "format": fmt, "rows": rows, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "text": text}
    if parsed:
        st.session_state["sf_uploaded"] = parsed
    if uploaded():
        st.dataframe(pd.DataFrame([{"Type": LABELS.get(k, k), "Code": k, "File": v.get("file"), "Rows": v.get("rows"), "Bytes": v.get("bytes"), "SHA256": v.get("sha256")} for k, v in uploaded().items()]), use_container_width=True, hide_index=True)


def reports() -> None:
    uploaded_reports = {k: str(v.get("text") or "") for k, v in uploaded().items() if v.get("format") in {"markdown", "text"}}
    if uploaded_reports:
        selected = st.selectbox("Uploaded report", sorted(uploaded_reports), format_func=lambda x: LABELS.get(x, x))
        st.markdown(uploaded_reports[selected])
        return
    paths = sorted(REPORTS_DIR.glob("*.md")) if REPORTS_DIR.exists() else []
    if not paths:
        empty("Markdown reports missing", "Upload .md from artifact or run report builders.")
        return
    selected = st.selectbox("Report", [str(p.relative_to(ROOT)) for p in paths])
    st.markdown((ROOT / selected).read_text(encoding="utf-8", errors="replace"))


def main() -> None:
    inject_css()
    hero()
    tabs = st.tabs(["* Signal Forge", "Raw", "FIFO", "Daily PnL", "Fee/Jito", "Triggers", "Reports", "Upload"])
    with tabs[0]:
        command_center()
    with tabs[1]:
        show_dataset("wallet_swaps")
    with tabs[2]:
        show_dataset("trades_paired")
    with tabs[3]:
        show_dataset("daily_pnl_calendar")
    with tabs[4]:
        show_dataset("priority_fee_jito_audit")
    with tabs[5]:
        show_dataset("trigger_tests")
    with tabs[6]:
        reports()
    with tabs[7]:
        upload()


if __name__ == "__main__":
    main()

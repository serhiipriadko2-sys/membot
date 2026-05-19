from __future__ import annotations

import hashlib
import io
from pathlib import Path
from typing import Any

import pandas as pd
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

st.set_page_config(page_title="membot · Iskra Forge", page_icon="🜂", layout="wide", initial_sidebar_state="expanded")


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
    .ritual{margin:22px auto;width:150px;height:150px;border-radius:50%;border:1px solid rgba(255,195,107,.25);position:relative;background:radial-gradient(circle,rgba(255,195,107,.18),transparent 10%,rgba(255,195,107,.04) 26%,transparent 58%)}.ritual:before{content:"";position:absolute;left:50%;top:-22px;bottom:-22px;width:2px;background:linear-gradient(180deg,transparent,var(--gold),transparent);box-shadow:0 0 16px rgba(255,195,107,.78);transform:translateX(-50%) rotate(7deg)}.ritual:after{content:"✦";position:absolute;inset:0;display:grid;place-items:center;font-size:38px;color:var(--gold);text-shadow:0 0 25px rgba(255,195,107,.9);animation:pulse 3.4s ease-in-out infinite}.copy{color:#DDD0B4;line-height:1.45}.tiny{color:#947F5D;font-size:.70rem;letter-spacing:.16em;text-transform:uppercase;margin-top:18px}
    .topbar{display:flex;gap:12px;align-items:center;justify-content:space-between;margin-bottom:14px}.search{flex:1;border:1px solid rgba(148,163,184,.16);background:rgba(2,5,12,.38);border-radius:12px;padding:10px 12px;color:#687386;font-size:.82rem}.cta{border:1px solid rgba(0,230,255,.48);color:#DFFBFF;border-radius:12px;padding:10px 13px;background:rgba(0,230,255,.07);box-shadow:0 0 22px rgba(0,230,255,.12);white-space:nowrap}.kicker{color:var(--gold);letter-spacing:.18em;text-transform:uppercase;font-size:.70rem;font-weight:800}.title{margin:.18rem 0 .28rem;font-size:clamp(2rem,4vw,3.45rem);line-height:.94;color:#FFF4D9}.subtitle{color:#BDC7D4;max-width:820px;margin:.35rem 0 0}
    .badges{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}.chip{border:1px solid rgba(148,163,184,.24);border-radius:999px;padding:7px 11px;background:rgba(11,14,20,.55);font-size:.78rem;color:#E9DECA}.ok{border-color:rgba(0,255,194,.34);color:#9FFFE9}.warn{border-color:rgba(255,195,107,.42);color:#FFD99A}.violet{border-color:rgba(122,92,255,.42);color:#CBBFFF}.hot{border-color:rgba(255,106,26,.42);color:#FFC0A0}
    .kpis{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin:16px 0}.kpi{padding:13px 12px;border:1px solid rgba(255,195,107,.14);border-radius:16px;background:rgba(5,8,14,.54)}.kpi span{display:block;color:#8E9AAD;font-size:.70rem;letter-spacing:.06em;text-transform:uppercase}.kpi strong{display:block;margin-top:4px;color:#F8EED5;font-size:1.12rem}
    .panel,.card,.empty{border:1px solid rgba(255,195,107,.17);border-radius:22px;background:linear-gradient(180deg,rgba(13,18,30,.74),rgba(5,8,14,.70));box-shadow:0 18px 46px rgba(0,0,0,.28),inset 0 1px 0 rgba(255,255,255,.04)}.panel{padding:18px 20px;margin-bottom:16px}.card{padding:15px 16px;height:100%}.small{font-size:.74rem;color:var(--muted);letter-spacing:.12em;text-transform:uppercase}.muted{color:var(--muted)}.empty{padding:18px 20px;border-style:dashed;border-color:rgba(255,195,107,.38)}.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
    .radar{height:174px;border-radius:18px;margin-top:10px;background:repeating-radial-gradient(circle,rgba(0,230,255,.22) 0 1px,transparent 1px 28px),conic-gradient(from 30deg,rgba(122,92,255,.55),rgba(0,230,255,.38),rgba(0,255,194,.25),rgba(122,92,255,.55));clip-path:polygon(50% 9%,84% 34%,76% 77%,50% 91%,20% 74%,17% 36%);opacity:.82;box-shadow:0 0 34px rgba(0,230,255,.18)}.orbit{height:155px;border-radius:50%;margin:10px auto 0;aspect-ratio:1/1;background:repeating-radial-gradient(circle,rgba(0,230,255,.45) 0 1px,transparent 2px 18px),conic-gradient(from 0deg,transparent,rgba(0,230,255,.8),transparent,rgba(255,195,107,.65),transparent);mask-image:radial-gradient(circle,transparent 0 32%,black 34% 100%)}.ladder{display:grid;gap:8px;margin-top:10px}.ladder div{display:grid;grid-template-columns:34px 1fr 44px;gap:10px;align-items:center;padding:8px 10px;border:1px solid rgba(255,195,107,.13);border-radius:14px;background:rgba(4,7,13,.42)}.ladder b{width:26px;height:26px;display:grid;place-items:center;border-radius:999px;border:1px solid rgba(255,195,107,.28);color:#FFE2AE}.progress{height:5px;border-radius:999px;background:rgba(255,255,255,.08);overflow:hidden;margin-top:8px}.progress i{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,var(--cyan),var(--mint),var(--gold))}.signal{border:1px solid rgba(148,163,184,.14);border-radius:15px;padding:10px;background:linear-gradient(90deg,rgba(122,92,255,.16),rgba(0,230,255,.06));display:grid;grid-template-columns:1fr auto;gap:10px;align-items:center;margin-top:9px}.sparkline{width:74px;height:28px;border-radius:9px;background:linear-gradient(135deg,transparent 40%,rgba(0,255,194,.7) 41% 45%,transparent 46%),linear-gradient(160deg,transparent 52%,rgba(255,195,107,.68) 53% 57%,transparent 58%),rgba(0,230,255,.06);border:1px solid rgba(0,230,255,.18)}.cluster{height:180px;border-radius:18px;margin-top:10px;background:radial-gradient(circle at 50% 50%,rgba(0,230,255,.92) 0 4px,rgba(0,230,255,.24) 5px 18px,transparent 20px),radial-gradient(circle at 22% 34%,rgba(122,92,255,.9) 0 4px,transparent 5px),radial-gradient(circle at 72% 24%,rgba(0,230,255,.78) 0 4px,transparent 5px),radial-gradient(circle at 84% 62%,rgba(255,106,26,.78) 0 4px,transparent 5px),rgba(3,6,12,.44)}.terminal{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:.77rem;color:#B7C3D1;display:grid;gap:6px;margin-top:10px}.terminal div{display:grid;grid-template-columns:46px 74px 78px 1fr;gap:7px;padding-bottom:6px;border-bottom:1px solid rgba(148,163,184,.08)}.style{display:grid;grid-template-columns:1.35fr 1.45fr 1.1fr 1fr;gap:12px;margin:16px 0 4px}.palette{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap}.swatch{width:54px;height:46px;border-radius:12px;border:1px solid rgba(255,255,255,.12)}.aa{font-size:3.4rem;color:#F3EAD9;line-height:.9}.keywords{display:grid;gap:7px;margin-top:10px;color:#C8D0DC}
    @media(max-width:1100px){.hero-grid,.style{grid-template-columns:1fr}.brand{border-right:0;border-bottom:1px solid rgba(255,195,107,.15)}.kpis{grid-template-columns:repeat(2,1fr)}.cards{grid-template-columns:1fr}}@media(max-width:760px){.block-container{padding-left:.78rem;padding-right:.78rem}.hero-grid{padding:16px}.title{font-size:2.15rem}.kpis{grid-template-columns:1fr}.terminal div{grid-template-columns:1fr 1fr}.ritual{width:118px;height:118px}.topbar{flex-direction:column;align-items:stretch}}
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


def local_df(name: str) -> pd.DataFrame:
    up = uploaded().get(name)
    if up and up.get("format") == "csv":
        return pd.read_csv(io.StringIO(str(up.get("text") or "")))
    return load_csv(str(DATASETS[name])) if name in DATASETS else pd.DataFrame()


def status_df() -> pd.DataFrame:
    rows = []
    for name, path in DATASETS.items():
        up = uploaded().get(name)
        exists = bool(up) or path.exists()
        rows.append({"Artifact": LABELS[name], "Code": name, "Found": exists, "File": up.get("file") if up else str(path.relative_to(ROOT)), "Rows": up.get("rows", 0) if up else (len(load_csv(str(path))) if exists else 0), "Bytes": up.get("bytes", 0) if up else (path.stat().st_size if exists else 0)})
    return pd.DataFrame(rows)


def find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    return next((c for c in candidates if c in df.columns), None)


def empty(title: str, body: str, command: str | None = None) -> None:
    h(f"<div class='empty'><h3>{title}</h3><p class='muted'>{body}</p>{'<code>'+command+'</code>' if command else ''}</div>")


def table(df: pd.DataFrame, key: str) -> None:
    if df.empty:
        return
    q = st.text_input("Фильтр", key=f"filter_{key}", placeholder="mint, signature, verdict, token...")
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
    <div class='hero'><div class='hero-grid'><aside class='brand'><div><div class='logo'><span class='sigil'>✦</span><span>membot</span></div><div class='copy' style='margin-top:18px'>Evidence First.<br/>Hypothesis Always.</div><div class='ritual'></div></div><div class='copy'><div class='tiny'>BUILT FOR TRUTH. NOT HYPE.</div></div></aside><section><div class='topbar'><div class='search'>⌕ Search wallet / token / signature... &nbsp; ⌘ K</div><div class='cta'>Analyze Wallet ✦</div></div><div class='kicker'>SIGNAL FORGE · SOLANA MEME INTELLIGENCE</div><div class='title'>raw truth<br/>before copy</div><p class='subtitle'>Forensic interface for wallet reverse-engineering: signatures, FIFO, fee/Jito audit, controls, and pre-buy hypotheses without pretending dashboard claims are raw truth.</p><div class='badges'><span class='chip ok'>🜂 Read-only</span><span class='chip violet'>Target {short}</span><span class='chip warn'>Dashboard ≠ SoT</span><span class='chip hot'>No blind copytrade</span></div><div class='kpis'><div class='kpi'><span>Wallet</span><strong>{short}</strong></div><div class='kpi'><span>Mode</span><strong>Forensic</strong></div><div class='kpi'><span>Truth Gate</span><strong>RAW → HYP</strong></div><div class='kpi'><span>Artifacts</span><strong>Required</strong></div><div class='kpi'><span>Verdict</span><strong>UNKNOWN</strong></div></div></section><aside><div class='panel'><div class='small'>SIGNATURE TRACE</div><div class='terminal'><div><span>now</span><span>guard</span><span>raw</span><span>evidence first</span></div><div><span>t-1</span><span>fifo</span><span>fees</span><span>Jito audit pending</span></div><div><span>t-2</span><span>hyp</span><span>entry</span><span>needs controls</span></div></div></div><div class='panel'><div class='small'>ISKRA KEYWORDS</div><div class='keywords'><span>⊙ Evidence First</span><span>✦ Signal Forge</span><span>⟁ Mythic Precision</span><span>⌁ On-chain Clarity</span></div></div></aside></div></div>
    """)


def command_center() -> None:
    status = status_df(); found = int(status["Found"].sum()); expected = len(status); critical = int(status[status["Code"].isin(CRITICAL)]["Found"].sum()); coverage = found / max(expected, 1)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Artifacts", f"{found}/{expected}"); c2.metric("Critical raw", f"{critical}/{len(CRITICAL)}"); c3.metric("Rows", int(status["Rows"].sum())); c4.metric("Coverage", f"{coverage:.0%}")
    if critical < len(CRITICAL):
        empty("Raw chain incomplete", "Для forensic verdict нужны Raw swaps, FIFO trades, Daily PnL и Fee/Jito. Пока один якорь отсутствует — держим UNKNOWN.", "GitHub Actions -> Run forensic verification -> limit=600 -> upload artifact")
    left, right = st.columns([2.2, 1.0], gap="large")
    with left:
        h(f"""
        <div class='panel'><div class='small'>WALLET OVERVIEW</div><h3>{TARGET_WALLET[:7]}...{TARGET_WALLET[-5:]}</h3><div class='badges'><span class='chip violet'>Watchlist</span><span class='chip ok'>Read-only</span><span class='chip warn'>Coverage {coverage:.0%}</span></div><div class='cards' style='margin-top:14px'><div class='card'><h3>Trigger Radar</h3><div class='radar'></div></div><div class='card'><h3>Truth Ladder</h3><div class='ladder'><div><b>5</b><strong>Confirmed</strong><span>raw</span></div><div><b>4</b><strong>Likely</strong><span>pattern</span></div><div><b>3</b><strong>Possible</strong><span>context</span></div><div><b>2</b><strong>Unknown</strong><span>missing</span></div></div></div><div class='card'><h3>Fee & Jito Audit</h3><div class='orbit'></div><div class='badges'><span class='chip warn'>UNKNOWN until CSV</span></div></div><div class='card'><h3>Raw Artifact Status</h3><div class='small'>critical chain</div><div class='progress'><i style='width:{critical / max(len(CRITICAL), 1) * 100:.0f}%'></i></div><p class='muted'>{critical}/{len(CRITICAL)} critical artifacts present.</p></div><div class='card'><h3>Daily PnL Calendar</h3><p class='muted'>Green-days can only be claimed after raw replay calendar exists.</p><div class='badges'><span class='chip warn'>No dashboard truth</span></div></div><div class='card'><h3>Pre-Buy Signal Forge</h3><div class='signal'><span>Smart Money Accumulation<br/><small class='muted'>hypothesis candidate</small></span><span class='sparkline'></span></div><div class='signal'><span>Liquidity Bootstrap<br/><small class='muted'>needs controls</small></span><span class='sparkline'></span></div></div></div></div>
        """)
        st.markdown("### Data deck"); st.dataframe(status, use_container_width=True, hide_index=True)
    with right:
        h("""<div class='panel'><div class='small'>CLUSTER MAP · 24H ACTIVITY</div><div class='cluster'></div><div class='badges'><span class='chip ok'>This Wallet</span><span class='chip violet'>Direct</span><span class='chip warn'>Indirect</span><span class='chip hot'>Unknown</span></div></div><div class='panel'><div class='small'>HYPOTHESIS NOTE</div><p class='muted'>Pattern candidates are research prompts. They need raw signatures, controls, and out-of-sample checks before any verdict.</p><div class='badges'><span class='chip violet'>Hypothesis</span><span class='chip warn'>Needs evidence</span></div></div>""")
    h("""<div class='style'><div class='panel'><div class='small'>SPARK PALETTE</div><div class='palette'><span class='swatch' style='background:#ffc36b'></span><span class='swatch' style='background:#ff6a1a'></span><span class='swatch' style='background:#7a5cff'></span><span class='swatch' style='background:#00e6ff'></span><span class='swatch' style='background:#00ffc2'></span><span class='swatch' style='background:#1a1f2b'></span><span class='swatch' style='background:#0b0e14'></span></div></div><div class='panel'><div class='small'>TYPOGRAPHY</div><div class='aa'>Aa</div><code>0x7A3F...9bK2</code></div><div class='panel'><div class='small'>DATA CHIPS</div><div class='badges'><span class='chip ok'>Confirmed</span><span class='chip warn'>Partial</span><span class='chip hot'>Pending</span><span class='chip violet'>High</span></div></div><div class='panel'><div class='small'>KEYWORDS</div><div class='keywords'><span>◎ Evidence First</span><span>✦ Forensic UI</span><span>⟁ Mythic Precision</span><span>⌁ Not financial advice</span></div></div></div>""")


def show_dataset(name: str) -> None:
    df = local_df(name)
    st.markdown(f"### {LABELS.get(name, name)}")
    if df.empty:
        empty(f"{LABELS.get(name, name)} отсутствует", "Загрузи CSV или запусти pipeline.")
        return
    c1, c2, c3 = st.columns(3); c1.metric("Rows", len(df)); c2.metric("Columns", len(df.columns)); c3.metric("Source", "upload/local")
    table(df, name)


def upload() -> None:
    st.markdown("### Upload run artifacts")
    files = st.file_uploader("CSV / MD / JSON / TXT", type=["csv", "md", "markdown", "json", "txt"], accept_multiple_files=True)
    parsed: dict[str, dict[str, Any]] = {}
    if not files and not uploaded():
        empty("Файлы ещё не загружены", "Скачай GitHub Actions artifact и загрузи CSV/MD сюда.")
        return
    for file in files or []:
        data = file.getvalue(); text = data.decode("utf-8", errors="replace"); fmt = "csv" if file.name.endswith(".csv") else ("markdown" if file.name.endswith((".md", ".markdown")) else "text")
        auto = next((t for t in KNOWN_TYPES if t != "other" and t in file.name.replace("-", "_")), "other")
        selected = st.selectbox(f"Тип: {file.name}", KNOWN_TYPES, index=KNOWN_TYPES.index(auto), key=f"type_{file.name}_{hashlib.sha256(data).hexdigest()[:8]}", format_func=lambda x: LABELS.get(x, x))
        rows = len(pd.read_csv(io.StringIO(text))) if fmt == "csv" else 0
        parsed[selected] = {"file": file.name, "format": fmt, "rows": rows, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "text": text}
    if parsed:
        st.session_state["sf_uploaded"] = parsed
    if uploaded():
        st.dataframe(pd.DataFrame([{"Тип": LABELS.get(k, k), "Код": k, "Файл": v.get("file"), "Строк": v.get("rows"), "Байт": v.get("bytes"), "SHA256": v.get("sha256")} for k, v in uploaded().items()]), use_container_width=True, hide_index=True)


def reports() -> None:
    paths = sorted(REPORTS_DIR.glob("*.md")) if REPORTS_DIR.exists() else []
    if not paths:
        empty("Markdown отчёты не найдены", "Загрузи `.md` из artifact или запусти report builders.")
        return
    selected = st.selectbox("Report", [str(p.relative_to(ROOT)) for p in paths])
    st.markdown((ROOT / selected).read_text(encoding="utf-8", errors="replace"))


def main() -> None:
    inject_css(); hero()
    tabs = st.tabs(["✦ Signal Forge", "Raw", "FIFO", "Daily PnL", "Fee/Jito", "Triggers", "Reports", "Upload"])
    with tabs[0]: command_center()
    with tabs[1]: show_dataset("wallet_swaps")
    with tabs[2]: show_dataset("trades_paired")
    with tabs[3]: show_dataset("daily_pnl_calendar")
    with tabs[4]: show_dataset("priority_fee_jito_audit")
    with tabs[5]: show_dataset("trigger_tests")
    with tabs[6]: reports()
    with tabs[7]: upload()


if __name__ == "__main__":
    main()

from __future__ import annotations

import hashlib
import io
import math
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from _agentic_layer import glossary_css, hint, render_agent_panel, render_onboarding

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
    "wallet_swaps": "Сырые swaps",
    "trades_paired": "FIFO-сделки",
    "daily_pnl_calendar": "PnL по дням",
    "priority_fee_jito_audit": "Fee/Jito аудит",
    "trigger_tests": "Pre-buy триггеры",
    "entry_exit_hypothesis_tests": "Гипотезы входа/выхода",
    "entry_context": "Контекст входа",
    "control_points": "Контрольные точки",
    "daily_pnl_calendar_report": "Отчёт PnL по дням",
    "priority_fee_jito_audit_report": "Отчёт Fee/Jito",
    "entry_exit_hypothesis_report": "Отчёт гипотез входа/выхода",
    "other": "Другое",
}
KNOWN_TYPES = [*DATASETS.keys(), "daily_pnl_calendar_report", "priority_fee_jito_audit_report", "entry_exit_hypothesis_report", "other"]

GOLD = "#FFC36B"
EMBER = "#FF6A1A"
VIOLET = "#7A5CFF"
CYAN = "#00E6FF"
MINT = "#00FFC2"
TEXT = "#F5EFE2"
MUTED = "#9CA8B7"

st.set_page_config(page_title="membot · Кузница Искры", layout="wide", initial_sidebar_state="expanded")


def inject_css() -> None:
    st.markdown(
        """
    <style>
    :root{--gold:#FFC36B;--ember:#FF6A1A;--violet:#7A5CFF;--cyan:#00E6FF;--mint:#00FFC2;--muted:#9CA8B7}
    html,body,[data-testid="stAppViewContainer"]{color:#F5EFE2;background:radial-gradient(circle at 4% 8%,rgba(255,195,107,.14),transparent 22%),radial-gradient(circle at 73% 0%,rgba(0,230,255,.14),transparent 24%),linear-gradient(180deg,#020305 0%,#070b12 46%,#05070d 100%)}
    [data-testid="stHeader"]{background:rgba(3,4,7,.56);backdrop-filter:blur(12px)}
    [data-testid="stSidebar"]{background:linear-gradient(180deg,rgba(2,3,7,.99),rgba(7,10,18,.96));border-right:1px solid rgba(255,195,107,.20)}
    .block-container{padding-top:.85rem;padding-bottom:4rem;max-width:1560px}
    .hero,.panel,.empty,.signal-card{border:1px solid rgba(255,195,107,.17);border-radius:22px;background:linear-gradient(180deg,rgba(13,18,30,.78),rgba(5,8,14,.70));box-shadow:0 18px 46px rgba(0,0,0,.28),inset 0 1px 0 rgba(255,255,255,.04)}
    .hero{position:relative;overflow:hidden;border-color:rgba(255,195,107,.28);border-radius:30px;margin-bottom:18px;padding:22px;background:radial-gradient(circle at 15% 35%,rgba(255,195,107,.18),transparent 26%),radial-gradient(circle at 75% 18%,rgba(0,230,255,.15),transparent 28%),linear-gradient(130deg,rgba(8,12,21,.97),rgba(10,17,30,.90))}
    .title{font-size:clamp(2rem,4vw,3.45rem);line-height:.94;color:#FFF4D9;margin:.2rem 0}.kicker,.small{color:var(--gold);letter-spacing:.14em;text-transform:uppercase;font-size:.72rem;font-weight:800}.muted{color:var(--muted)}
    .badges{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}.chip{border:1px solid rgba(148,163,184,.24);border-radius:999px;padding:7px 11px;background:rgba(11,14,20,.55);font-size:.78rem;color:#E9DECA}.ok{border-color:rgba(0,255,194,.34);color:#9FFFE9}.warn{border-color:rgba(255,195,107,.42);color:#FFD99A}.violet{border-color:rgba(122,92,255,.42);color:#CBBFFF}.hot{border-color:rgba(255,106,26,.42);color:#FFC0A0}
    .panel,.empty,.signal-card{padding:16px 18px;margin-bottom:14px}.empty{border-style:dashed;border-color:rgba(255,195,107,.38)}.signal-card h4{margin:.1rem 0 .3rem;color:#FFF4D9}.signal-meta{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}.signal-bar{height:6px;background:rgba(255,255,255,.08);border-radius:999px;overflow:hidden;margin-top:10px}.signal-bar i{display:block;height:100%;background:linear-gradient(90deg,var(--cyan),var(--mint),var(--gold));border-radius:999px}.progress{height:5px;border-radius:999px;background:rgba(255,255,255,.08);overflow:hidden;margin-top:8px}.progress i{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,var(--cyan),var(--mint),var(--gold))}
    """
        + glossary_css()
        + "</style>",
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
            "Артефакт": LABELS[name],
            "Код": name,
            "Найден": exists,
            "Файл": up.get("file") if up else str(path.relative_to(ROOT)),
            "Строк": up.get("rows", 0) if up else (len(load_csv(str(path))) if exists else 0),
            "Байт": up.get("bytes", 0) if up else (path.stat().st_size if exists else 0),
        })
    return pd.DataFrame(rows)


def find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    return next((c for c in candidates if c in df.columns), None)


def plotly_layout(fig: go.Figure, height: int = 280) -> go.Figure:
    fig.update_layout(height=height, margin=dict(l=8, r=8, t=34, b=8), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT, family="Inter, system-ui, sans-serif"), hoverlabel=dict(bgcolor="#0B0E14", font_color=TEXT, bordercolor=GOLD), legend=dict(orientation="h", y=-0.16, x=0, bgcolor="rgba(0,0,0,0)"))
    fig.update_xaxes(gridcolor="rgba(255,195,107,0.08)", zeroline=False, color=MUTED)
    fig.update_yaxes(gridcolor="rgba(255,195,107,0.08)", zeroline=False, color=MUTED)
    return fig


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
    <div class='hero'>
      <div class='kicker'>КУЗНИЦА СИГНАЛОВ · SOLANA MEME INTELLIGENCE</div>
      <div class='title'>сырая правда<br/>до копирования</div>
      <p class='muted'>Forensic-интерфейс для reverse-engineering кошелька: {hint('signature', 'signatures')}, {hint('fifo', 'FIFO')}, {hint('jito', 'fee/Jito аудит')}, {hint('cluster_context', 'cluster_context')}, {hint('repeat_wave', 'repeat_wave')}, {hint('price_action', 'price_action')}, {hint('cross_chain_regime', 'cross_chain_regime')} и {hint('trigger', 'pre-buy гипотезы')}.</p>
      <div class='badges'><span class='chip ok'>Только чтение</span><span class='chip violet'>Цель {short}</span><span class='chip warn'>Dashboard != SoT</span><span class='chip hot'>Не копитрейдить вслепую</span></div>
    </div>
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
    tmp["_amount"] = pd.to_numeric(tmp[amount_col], errors="coerce").abs().fillna(0) if amount_col else 1.0
    grouped = tmp.groupby("_token", dropna=False).agg(tx_count=("_token", "size"), buy=("_buy", "sum"), sell=("_sell", "sum"), amount=("_amount", "sum")).reset_index().sort_values(["tx_count", "amount"], ascending=False).head(18)
    if grouped.empty:
        return None
    max_count = max(float(grouped["tx_count"].max()), 1.0)
    grouped["x"] = [(1.0 + 0.52 * (float(c) / max_count)) * math.cos((2 * math.pi * i / max(len(grouped), 1)) - math.pi / 2) for i, c in enumerate(grouped["tx_count"].tolist())]
    grouped["y"] = [(1.0 + 0.52 * (float(c) / max_count)) * math.sin((2 * math.pi * i / max(len(grouped), 1)) - math.pi / 2) for i, c in enumerate(grouped["tx_count"].tolist())]
    grouped["balance"] = grouped["buy"] - grouped["sell"]
    fig = go.Figure()
    for _, row in grouped.iterrows():
        fig.add_trace(go.Scatter(x=[0, row["x"]], y=[0, row["y"]], mode="lines", line=dict(color="rgba(0,230,255,0.20)", width=1), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=[0], y=[0], mode="markers+text", marker=dict(size=34, color=GOLD, line=dict(color=CYAN, width=2)), text=["wallet"], textposition="bottom center", name="целевой кошелёк", hovertext=[TARGET_WALLET], hoverinfo="text"))
    fig.add_trace(go.Scatter(x=grouped["x"], y=grouped["y"], mode="markers+text", marker=dict(size=12 + 34 * grouped["tx_count"] / max_count, color=grouped["balance"], colorscale=[[0, EMBER], [0.5, VIOLET], [1, MINT]], showscale=False, line=dict(color="rgba(255,195,107,0.55)", width=1)), text=grouped["_token"], textposition="top center", name="токены", hovertemplate="token=%{text}<br>tx=%{customdata[0]}<br>buy=%{customdata[1]}<br>sell=%{customdata[2]}<br>amount=%{customdata[3]:.4f}<extra></extra>", customdata=grouped[["tx_count", "buy", "sell", "amount"]].to_numpy()))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False, scaleanchor="x", scaleratio=1)
    fig.update_layout(title="Карта кластеров по частоте взаимодействия с токенами", showlegend=False)
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
    pivot = df.pivot_table(index="_weekday", columns="_week", values="_pnl", aggfunc="sum").reindex(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    if pivot.empty:
        return None
    fig = go.Figure(data=go.Heatmap(z=pivot.to_numpy(), x=list(pivot.columns), y=list(pivot.index), colorscale=[[0, EMBER], [0.5, "#1A1F2B"], [1, MINT]], zmid=0, hovertemplate="week=%{x}<br>day=%{y}<br>pnl=%{z:.4f}<extra></extra>"))
    fig.update_layout(title="Календарь PnL по raw/FIFO артефакту")
    return plotly_layout(fig, height=300)


def build_fee_figure(fee: pd.DataFrame) -> go.Figure | None:
    if fee.empty:
        return None
    verdict_col = find_col(fee, ["verdict", "fee_verdict", "evidence_verdict"])
    jito_col = find_col(fee, ["has_jito_tip", "jito_tip", "jito_detected"])
    cb_col = find_col(fee, ["has_compute_budget_ix", "compute_budget", "has_priority_fee"])
    labels, values = [], []
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
    fig.update_layout(title="Fee/Jito орбита доказательств")
    return plotly_layout(fig, height=300)


def trigger_source_df() -> pd.DataFrame:
    trig = local_df("trigger_tests")
    return trig if not trig.empty else local_df("entry_exit_hypothesis_tests")


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
    name_col = find_col(triggers, ["hypothesis_id", "trigger", "hypothesis", "feature", "name", "family", "scope"])
    status_col = find_col(triggers, ["status", "verdict", "result"])
    score_col = find_col(triggers, ["support_rate_pct", "score", "confidence", "support", "lift", "precision", "win_rate", "value"])
    if name_col is None:
        return None
    df = triggers.copy().head(24)
    df["_score"] = df.apply(lambda row: score_for_row(row, score_col, status_col), axis=1)
    grouped = df.groupby(name_col, dropna=False)["_score"].mean().sort_values(ascending=False).head(8)
    if grouped.empty:
        return None
    fig = go.Figure(data=go.Scatterpolar(r=grouped.values.tolist(), theta=[str(i)[:22] for i in grouped.index.tolist()], fill="toself", line=dict(color=CYAN, width=2), marker=dict(color=GOLD, size=7), name="поддержка"))
    fig.update_layout(title="Радар pre-buy гипотез", polar=dict(bgcolor="rgba(0,0,0,0)", radialaxis=dict(range=[0, 100], gridcolor="rgba(255,195,107,0.12)", tickfont=dict(color=MUTED)), angularaxis=dict(gridcolor="rgba(255,195,107,0.10)", tickfont=dict(color=TEXT))), showlegend=False)
    return plotly_layout(fig, height=330)


def render_signal_cards(triggers: pd.DataFrame) -> None:
    if triggers.empty:
        empty("Карточкам сигналов нужны строки триггеров", "Загрузи trigger_tests.csv или entry_exit_hypothesis_tests.csv, чтобы панель стала живой.")
        return
    name_col = find_col(triggers, ["hypothesis_id", "trigger", "hypothesis", "feature", "name", "family", "scope"])
    status_col = find_col(triggers, ["status", "verdict", "result"])
    score_col = find_col(triggers, ["support_rate_pct", "score", "confidence", "support", "lift", "precision", "win_rate", "value"])
    note_col = find_col(triggers, ["evidence", "notes", "summary", "description", "reason"])
    df = triggers.copy().head(12)
    df["_score"] = df.apply(lambda row: score_for_row(row, score_col, status_col), axis=1)
    df = df.sort_values("_score", ascending=False).head(5)
    cards = []
    for _, row in df.iterrows():
        name = str(row.get(name_col, "Кандидат сигнала"))[:80] if name_col else "Кандидат сигнала"
        status = str(row.get(status_col, "UNKNOWN"))[:36] if status_col else "UNKNOWN"
        note = str(row.get(note_col, "Нужны raw replay и controls."))[:140] if note_col else "Нужны raw replay и controls."
        score = float(row["_score"])
        cls = "ok" if score >= 75 else "warn" if score >= 35 else "hot"
        cards.append(f"<div class='signal-card'><div class='small'>ЖИВАЯ КАРТОЧКА СИГНАЛА</div><h4>{name}</h4><p class='muted'>{note}</p><div class='signal-meta'><span class='chip {cls}'>{status}</span><span class='chip violet'>score {score:.0f}</span></div><div class='signal-bar'><i style='width:{score:.0f}%'></i></div></div>")
    h("".join(cards))


def render_plot(fig: go.Figure | None, title: str, body: str, key: str) -> None:
    if fig is None:
        empty(title, body)
    else:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True}, key=key)


def get_current_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    status = status_df()
    return status, local_df("wallet_swaps"), local_df("trades_paired"), local_df("daily_pnl_calendar"), local_df("priority_fee_jito_audit"), trigger_source_df()


def command_center() -> None:
    status, swaps, trades, daily, fee, triggers = get_current_frames()
    found = int(status["Найден"].sum())
    expected = len(status)
    critical = int(status[status["Код"].isin(CRITICAL)]["Найден"].sum())
    coverage = found / max(expected, 1)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Артефакты", f"{found}/{expected}")
    c2.metric("Критический raw", f"{critical}/{len(CRITICAL)}")
    c3.metric("Строки", int(status["Строк"].sum()))
    c4.metric("Покрытие", f"{coverage:.0%}")
    if critical < len(CRITICAL):
        empty("Raw-цепочка неполная", "Для forensic-вердикта нужны raw swaps, FIFO trades, Daily PnL и Fee/Jito. Без якорей verdict остаётся UNKNOWN.", "GitHub Actions -> Run forensic verification -> limit=600 -> upload artifact")
    left, right = st.columns([2.2, 1.0], gap="large")
    with left:
        h(f"""<div class='panel'><div class='small'>ОБЗОР КОШЕЛЬКА</div><h3>{TARGET_WALLET[:7]}...{TARGET_WALLET[-5:]}</h3><div class='badges'><span class='chip violet'>Watchlist</span><span class='chip ok'>Только чтение</span><span class='chip warn'>Покрытие {coverage:.0%}</span></div></div>""")
        chart_cols = st.columns(2)
        with chart_cols[0]:
            render_plot(build_trigger_radar_figure(triggers), "Радар триггеров ждёт данные", "Загрузи trigger tests или entry/exit hypothesis rows.", key="forge_trigger_radar")
        with chart_cols[1]:
            render_plot(build_fee_figure(fee), "Fee/Jito орбита ждёт данные", "Загрузи priority_fee_jito_audit.csv.", key="forge_fee_orbit")
        render_plot(build_daily_calendar_figure(daily), "Календарь PnL ждёт данные", "Загрузи daily_pnl_calendar.csv.", key="forge_daily_calendar")
        h(f"""<div class='panel'><div class='small'>{hint('artifact', 'СТАТУС RAW-АРТЕФАКТОВ')}</div><div class='progress'><i style='width:{critical / max(len(CRITICAL), 1) * 100:.0f}%'></i></div><p class='muted'>{critical}/{len(CRITICAL)} критических артефактов найдено.</p></div>""")
        st.markdown("### Дека данных")
        st.dataframe(status, use_container_width=True, hide_index=True)
    with right:
        h(f"""<div class='panel'><div class='small'>{hint('cluster_map', 'КАРТА КЛАСТЕРОВ · ВЗАИМОДЕЙСТВИЕ С ТОКЕНАМИ')}</div>""")
        render_plot(build_cluster_figure(swaps, trades), "Карта кластеров ждёт raw swaps", "Загрузи wallet_swaps.csv или trades_paired.csv.", key="forge_cluster_map")
        h("</div>")
        h(f"""<div class='panel'><div class='small'>{hint('signal_card', 'PRE-BUY КАРТОЧКИ СИГНАЛОВ')}</div><p class='muted'>Карточки сортируются по score/status. PASS — поддержка гипотезы, не команда покупки.</p></div>""")
        render_signal_cards(triggers)


def show_dataset(name: str) -> None:
    df = local_df(name)
    st.markdown(f"### {LABELS.get(name, name)}")
    if df.empty:
        empty(f"{LABELS.get(name, name)} отсутствует", "Загрузи CSV, подтяни Supabase run или запусти pipeline.")
        return
    c1, c2, c3 = st.columns(3)
    c1.metric("Строки", len(df))
    c2.metric("Колонки", len(df.columns))
    c3.metric("Источник", "upload/supabase/local")
    if name == "daily_pnl_calendar":
        render_plot(build_daily_calendar_figure(df), "Календарь недоступен", "Не найдены date и pnl columns.", key=f"dataset_{name}_calendar")
    elif name == "priority_fee_jito_audit":
        render_plot(build_fee_figure(df), "Fee/Jito график недоступен", "Не найдены verdict/Jito/ComputeBudget columns.", key=f"dataset_{name}_fee")
    elif name in {"trigger_tests", "entry_exit_hypothesis_tests"}:
        render_plot(build_trigger_radar_figure(df), "Радар триггеров недоступен", "Не найдены trigger/status columns.", key=f"dataset_{name}_radar")
        render_signal_cards(df)
    elif name in {"wallet_swaps", "trades_paired"}:
        render_plot(build_cluster_figure(df, pd.DataFrame()), "Карта кластеров недоступна", "Не найдены token/mint columns.", key=f"dataset_{name}_cluster")
    table(df, name)


def upload() -> None:
    st.markdown("### Загрузка артефактов run")
    files = st.file_uploader("CSV / MD / JSON / TXT", type=["csv", "md", "markdown", "json", "txt"], accept_multiple_files=True)
    parsed: dict[str, dict[str, Any]] = {}
    if not files and not uploaded():
        empty("Файлы ещё не загружены", "Скачай GitHub Actions artifact и загрузи CSV/MD сюда или подтяни run через Data Bridge.")
        return
    for file in files or []:
        data = file.getvalue()
        text = data.decode("utf-8", errors="replace")
        fmt = "csv" if file.name.endswith(".csv") else ("markdown" if file.name.endswith((".md", ".markdown")) else "text")
        auto = next((t for t in KNOWN_TYPES if t != "other" and t in file.name.replace("-", "_")), "other")
        selected = st.selectbox(f"Тип: {file.name}", KNOWN_TYPES, index=KNOWN_TYPES.index(auto), key=f"type_{file.name}_{hashlib.sha256(data).hexdigest()[:8]}", format_func=lambda x: LABELS.get(x, x))
        rows = len(df_from_text(text)) if fmt == "csv" else 0
        parsed[selected] = {"file": file.name, "format": fmt, "rows": rows, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "text": text}
    if parsed:
        st.session_state["sf_uploaded"] = parsed
    if uploaded():
        st.dataframe(pd.DataFrame([{"Тип": LABELS.get(k, k), "Код": k, "Файл": v.get("file"), "Строк": v.get("rows"), "Байт": v.get("bytes"), "SHA256": v.get("sha256")} for k, v in uploaded().items()]), use_container_width=True, hide_index=True)


def reports() -> None:
    uploaded_reports = {k: str(v.get("text") or "") for k, v in uploaded().items() if v.get("format") in {"markdown", "text"}}
    if uploaded_reports:
        selected = st.selectbox("Загруженный отчёт", sorted(uploaded_reports), format_func=lambda x: LABELS.get(x, x))
        st.markdown(uploaded_reports[selected])
        return
    paths = sorted(REPORTS_DIR.glob("*.md")) if REPORTS_DIR.exists() else []
    if not paths:
        empty("Markdown-отчёты отсутствуют", "Загрузи .md из artifact или запусти report builders.")
        return
    selected = st.selectbox("Отчёт", [str(p.relative_to(ROOT)) for p in paths])
    st.markdown((ROOT / selected).read_text(encoding="utf-8", errors="replace"))


def guide_and_agent() -> None:
    status, swaps, trades, daily, fee, triggers = get_current_frames()
    render_onboarding(status)
    render_agent_panel(status, swaps, trades, daily, fee, triggers)


def main() -> None:
    inject_css()
    hero()
    tabs = st.tabs(["Кузница сигналов", "Гайд / Агент", "Raw", "FIFO", "PnL по дням", "Fee/Jito", "Триггеры", "Отчёты", "Загрузка"])
    with tabs[0]:
        command_center()
    with tabs[1]:
        guide_and_agent()
    with tabs[2]:
        show_dataset("wallet_swaps")
    with tabs[3]:
        show_dataset("trades_paired")
    with tabs[4]:
        show_dataset("daily_pnl_calendar")
    with tabs[5]:
        show_dataset("priority_fee_jito_audit")
    with tabs[6]:
        show_dataset("trigger_tests")
        show_dataset("entry_exit_hypothesis_tests")
    with tabs[7]:
        reports()
    with tabs[8]:
        upload()


if __name__ == "__main__":
    main()

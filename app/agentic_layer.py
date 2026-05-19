from __future__ import annotations

from html import escape
from typing import Any

import pandas as pd
import streamlit as st


GLOSSARY: dict[str, dict[str, str]] = {
    "artifact": {"title": "Artifact", "simple": "Файл-результат прогона: CSV, JSON или отчёт.", "why": "Без артефакта интерфейс не имеет права делать выводы."},
    "raw": {"title": "Raw", "simple": "Сырые данные из сети без красивой обработки.", "why": "Это нижний слой правды: signatures, transactions, swaps."},
    "signature": {"title": "Signature", "simple": "Уникальный ID транзакции в Solana.", "why": "По signature можно поднять исходную транзакцию и проверить факт."},
    "transaction": {"title": "Transaction", "simple": "Полная запись действия в сети: инструкции, fee, балансы, программы.", "why": "Только transaction payload позволяет проверить swap, fee и маршрутизацию."},
    "wallet": {"title": "Wallet", "simple": "Адрес кошелька, который мы изучаем.", "why": "Это объект forensic-анализа, не источник истины сам по себе."},
    "token_mint": {"title": "Token mint", "simple": "Адрес токена в Solana.", "why": "Он нужен, чтобы не путать токены с похожими названиями."},
    "fifo": {"title": "FIFO", "simple": "Метод учёта: что купили раньше, то продаём раньше.", "why": "Нужен для честного PnL, когда много покупок/продаж одного токена."},
    "pnl": {"title": "PnL", "simple": "Profit and Loss: прибыль или убыток.", "why": "Показывает итог сделки/дня после сопоставления входов и выходов."},
    "daily_pnl": {"title": "Daily PnL", "simple": "PnL по дням.", "why": "Green-days claim можно проверять только по этому артефакту, а не по витрине."},
    "fee": {"title": "Fee", "simple": "Комиссия за транзакцию.", "why": "Может съесть прибыль, особенно при частых сделках."},
    "priority_fee": {"title": "Priority fee", "simple": "Доплата валидаторам/сети за приоритет исполнения.", "why": "Помогает понять, бот ли это и насколько агрессивно он борется за скорость."},
    "jito": {"title": "Jito", "simple": "Инфраструктура/механизм Solana для MEV и tips.", "why": "Jito tip может указывать на MEV/скоростную стратегию, но сам по себе не доказывает edge."},
    "compute_budget": {"title": "ComputeBudget", "simple": "Инструкции Solana, задающие лимиты/цену compute units.", "why": "Часто встречается у ботов; это не всегда MEV, но важный сигнал."},
    "cluster_map": {"title": "Cluster map", "simple": "Карта связей кошелька с токенами/кластерами активности.", "why": "Помогает увидеть, куда кошелёк чаще всего входит и где концентрация действий."},
    "trigger": {"title": "Trigger", "simple": "Условие, которое могло сработать до покупки.", "why": "Это гипотеза входа, а не команда покупать."},
    "signal_card": {"title": "Signal card", "simple": "Карточка гипотезы: что заметили, насколько поддержано данными, что проверить.", "why": "Держит вывод в форме evidence, а не слепого сигнала."},
    "hypothesis": {"title": "Hypothesis", "simple": "Проверяемое предположение.", "why": "Пока нет raw replay и контроля — это не факт."},
    "support_rate": {"title": "Support rate", "simple": "Процент строк/кейсов, где гипотеза получила поддержку.", "why": "Это не точность стратегии, а только первичная мера совпадения."},
    "confidence": {"title": "Confidence", "simple": "Насколько мы уверены в выводе.", "why": "Уверенность падает, если мало raw данных, есть RPC errors или пустой FIFO."},
    "coverage": {"title": "Coverage", "simple": "Какая доля нужных данных реально есть.", "why": "Если coverage низкий, красивые графики не являются доказательством."},
    "rpc": {"title": "RPC", "simple": "Узел/API, через который мы читаем Solana.", "why": "Публичный RPC может дать 429 и испортить выборку."},
    "supabase": {"title": "Supabase", "simple": "База, где можно хранить прогоны и артефакты.", "why": "Позволяет возвращаться к прошлым run без ручной загрузки файлов."},
    "sot": {"title": "SoT", "simple": "Source of Truth: источник истины.", "why": "Для membot SoT — raw artifacts/repo docs, не dashboard-картинка."},
    "green_days": {"title": "Green-days", "simple": "Дни, где итоговый PnL положительный.", "why": "Claim MATCH только если daily calendar построен из raw/FIFO."},
    "verdict": {"title": "Verdict", "simple": "Итоговая метка проверки: PASS, PARTIAL, UNKNOWN, DRIFT.", "why": "Она должна объяснять, что доказано, а что нет."},
    "agent": {"title": "Agent", "simple": "ИИ-слой, который помогает читать данные, задавать вопросы и предлагать следующий безопасный шаг.", "why": "Агент не торгует и не заменяет raw-проверку."},
}

FAQ: list[tuple[str, str]] = [
    ("Почему нельзя просто копировать кошелёк?", "Потому что dashboard показывает витрину, а не задержки, fee, маршруты агрегатора, неудачные legs и условия входа. Сначала raw -> FIFO -> fee/Jito -> context -> только потом гипотеза."),
    ("Что значит UNKNOWN?", "Это честная метка: данных недостаточно. Например, daily_pnl_calendar пустой или transactions_raw покрывает 2 из 600 signatures."),
    ("Почему нужен хороший RPC?", "Без стабильного RPC transaction payloads не скачиваются. Public RPC может вернуть 429, и тогда графики будут красивыми, но выборка сломана."),
    ("Что делает Supabase Bridge?", "Берёт сохранённый run из Supabase и загружает его в текущую сессию Iskra Forge, чтобы графики ожили без ручного upload."),
    ("Что такое agent layer в этом приложении?", "Это слой рабочих агентов: Onboarding, Data, Fee/Jito, Trigger, Verdict. Он читает только доступные артефакты и объясняет следующий шаг."),
    ("Агент может дать BUY/SELL?", "Нет. В этом проекте агент только объясняет, проверяет, резюмирует и предлагает безопасный research-step."),
    ("Почему PASS не равен сигналу покупки?", "PASS означает, что конкретный UI/данный/тест имеет поддержку. Это не доказывает edge и не учитывает latency, liquidity, slippage и риск исполнения."),
    ("Какие файлы нужны для нормальной проверки?", "wallet_swaps.csv, trades_paired.csv, daily_pnl_calendar.csv, priority_fee_jito_audit.csv, reports/*.md и raw signatures/transactions."),
]


def hint(term: str, label: str | None = None) -> str:
    item = GLOSSARY.get(term, {"title": term, "simple": "Термин пока не описан.", "why": "Добавь его в glossary."})
    label_html = escape(label or item["title"])
    return (
        f"<span class='hint-wrap'><span>{label_html}</span>"
        f"<details class='hint'><summary>?</summary>"
        f"<div class='hint-card'><b>{escape(item['title'])}</b>"
        f"<p>{escape(item['simple'])}</p><small>{escape(item['why'])}</small></div>"
        f"</details></span>"
    )


def glossary_css() -> str:
    return """
    .hint-wrap{display:inline-flex;align-items:center;gap:.35rem;vertical-align:middle}
    .hint{display:inline-block;position:relative}
    .hint summary{list-style:none;width:18px;height:18px;border-radius:999px;display:inline-grid;place-items:center;cursor:pointer;background:rgba(255,195,107,.12);border:1px solid rgba(255,195,107,.28);color:rgba(255,244,217,.72);font-size:.68rem;line-height:1;box-shadow:0 0 18px rgba(255,195,107,.08)}
    .hint summary::-webkit-details-marker{display:none}
    .hint-card{position:absolute;z-index:30;right:0;top:24px;width:min(310px,82vw);padding:12px 14px;border-radius:16px;background:rgba(5,8,14,.96);border:1px solid rgba(255,195,107,.24);box-shadow:0 18px 50px rgba(0,0,0,.52);backdrop-filter:blur(14px);color:#F5EFE2;text-transform:none;letter-spacing:0;font-size:.9rem}
    .hint-card p{margin:.35rem 0;color:#B7C3D1}.hint-card small{color:#FFC36B}.onboard-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:12px 0}.onboard-card{border:1px solid rgba(255,195,107,.17);border-radius:18px;padding:14px 16px;background:linear-gradient(180deg,rgba(13,18,30,.78),rgba(5,8,14,.70));min-height:132px}.onboard-card b{color:#FFF4D9}.onboard-card p{color:#9CA8B7}.agent-plan{border-left:2px solid rgba(0,230,255,.48);padding-left:12px;color:#B7C3D1}.agent-badge{display:inline-block;margin:.18rem .28rem .18rem 0;padding:.24rem .55rem;border-radius:999px;border:1px solid rgba(255,195,107,.22);background:rgba(255,195,107,.06);color:#FFE1A8;font-size:.78rem}@media(max-width:900px){.onboard-grid{grid-template-columns:1fr}.hint-card{right:auto;left:-30px}}
    """


def render_onboarding(status: pd.DataFrame) -> None:
    found = int(status["Found"].sum()) if not status.empty and "Found" in status else 0
    rows = int(status["Rows"].sum()) if not status.empty and "Rows" in status else 0
    st.markdown("### Онбординг: как читать membot")
    st.markdown(
        f"""
        <div class='onboard-grid'>
          <div class='onboard-card'><b>1. Сначала raw</b><p>{hint('raw', 'Raw')} и {hint('signature', 'signatures')} отвечают на вопрос: что реально было в сети.</p></div>
          <div class='onboard-card'><b>2. Потом учёт</b><p>{hint('fifo', 'FIFO')} и {hint('pnl', 'PnL')} превращают swaps в проверяемые результаты.</p></div>
          <div class='onboard-card'><b>3. Потом гипотезы</b><p>{hint('trigger', 'Triggers')} и {hint('hypothesis', 'hypotheses')} — это research, не BUY-сигнал.</p></div>
        </div>
        <div class='panel'><div class='small'>CURRENT DATA STATE</div>
        <p class='muted'>Артефактов найдено: <b>{found}</b>. Строк в доступных таблицах: <b>{rows}</b>. Если coverage низкий — выводы держим в UNKNOWN/PARTIAL.</p></div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Частые вопросы")
    for i, (q, a) in enumerate(FAQ, start=1):
        with st.expander(q, key=f"faq_{i}"):
            st.write(a)

    st.markdown("### Словарь терминов")
    query = st.text_input("Поиск по словарю", key="glossary_search", placeholder="FIFO, Jito, RPC, PnL...")
    items = GLOSSARY.items()
    if query:
        q = query.lower().strip()
        items = [(k, v) for k, v in items if q in k.lower() or q in v["title"].lower() or q in v["simple"].lower()]
    cols = st.columns(2)
    for idx, (_, item) in enumerate(items):
        with cols[idx % 2]:
            st.markdown(f"**{item['title']}**  \n{item['simple']}  \n:gray[{item['why']}]")


def _row_count(df: pd.DataFrame) -> int:
    return 0 if df is None or df.empty else int(len(df))


def build_agent_context(status: pd.DataFrame, swaps: pd.DataFrame, trades: pd.DataFrame, daily: pd.DataFrame, fee: pd.DataFrame, triggers: pd.DataFrame) -> dict[str, Any]:
    return {
        "artifacts_found": int(status["Found"].sum()) if not status.empty and "Found" in status else 0,
        "artifact_rows": int(status["Rows"].sum()) if not status.empty and "Rows" in status else 0,
        "swaps_rows": _row_count(swaps),
        "trades_rows": _row_count(trades),
        "daily_rows": _row_count(daily),
        "fee_rows": _row_count(fee),
        "trigger_rows": _row_count(triggers),
        "missing_critical": status[(status["Code"].isin(["wallet_swaps", "trades_paired", "daily_pnl_calendar", "priority_fee_jito_audit"])) & (~status["Found"])] ["Artifact"].tolist() if not status.empty and {"Code", "Found", "Artifact"}.issubset(status.columns) else [],
    }


def agent_reply(question: str, ctx: dict[str, Any]) -> str:
    q = question.lower()
    missing = ctx.get("missing_critical", [])
    health = (
        f"Artifacts={ctx.get('artifacts_found', 0)}, rows={ctx.get('artifact_rows', 0)}, "
        f"swaps={ctx.get('swaps_rows', 0)}, fifo={ctx.get('trades_rows', 0)}, "
        f"daily={ctx.get('daily_rows', 0)}, fee={ctx.get('fee_rows', 0)}, triggers={ctx.get('trigger_rows', 0)}."
    )

    if any(word in q for word in ["что дальше", "next", "следующий", "делать"]):
        if missing:
            return f"**Следующий шаг:** закрыть missing critical artifacts: {', '.join(missing)}. Сейчас состояние: `{health}`. Без этого verdict остаётся PARTIAL/UNKNOWN."
        if ctx.get("daily_rows", 0) == 0:
            return f"**Следующий шаг:** пересобрать daily PnL/FIFO. Raw swaps есть, но daily calendar пустой. Сейчас: `{health}`."
        return f"**Следующий шаг:** читать отчёты и сверять гипотезы с controls. Сейчас данные выглядят достаточно полными для первичного QA: `{health}`."

    if "jito" in q or "fee" in q or "compute" in q:
        return f"**Fee/Jito agent:** fee rows={ctx.get('fee_rows', 0)}. Jito/priority вывод нельзя делать без `priority_fee_jito_audit.csv`. Если видишь COMPUTE_BUDGET_ONLY — это признак compute-budget поведения, но не доказательство MEV."

    if "green" in q or "pnl" in q or "profit" in q:
        return f"**PnL agent:** daily rows={ctx.get('daily_rows', 0)}, FIFO rows={ctx.get('trades_rows', 0)}. Green-days MATCH возможен только если daily calendar не пустой и построен после FIFO."

    if "trigger" in q or "сигнал" in q or "buy" in q or "покуп" in q:
        return f"**Trigger agent:** trigger rows={ctx.get('trigger_rows', 0)}. Даже PASS — это поддержка гипотезы, не BUY-команда. Нужны controls, liquidity, latency и out-of-sample."

    if "объяс" in q or "термин" in q or "faq" in q:
        return "**Onboarding agent:** открой вкладку `Guide/Agent` и используй словарь. Каждый знак `?` рядом с термином раскрывает простое объяснение и зачем термин нужен."

    return f"**SIFT agent:** я могу объяснить термин, проверить готовность артефактов или предложить следующий безопасный шаг. Текущий snapshot: `{health}`."


def render_agent_panel(status: pd.DataFrame, swaps: pd.DataFrame, trades: pd.DataFrame, daily: pd.DataFrame, fee: pd.DataFrame, triggers: pd.DataFrame) -> None:
    ctx = build_agent_context(status, swaps, trades, daily, fee, triggers)
    st.markdown("### Агентурный слой Искры")
    st.markdown(
        "<span class='agent-badge'>Onboarding Agent</span><span class='agent-badge'>Data QA Agent</span><span class='agent-badge'>Fee/Jito Agent</span><span class='agent-badge'>Trigger Agent</span><span class='agent-badge'>Verdict Guard</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='panel'><div class='small'>AGENT BOUNDARY</div><p class='muted'>Агент объясняет, проверяет, резюмирует и предлагает следующий research-step. Он не хранит секреты и не выдаёт BUY/SELL.</p></div>",
        unsafe_allow_html=True,
    )

    if "agent_messages" not in st.session_state:
        st.session_state.agent_messages = [
            {"role": "assistant", "content": "Я агент membot. Спроси: `что дальше?`, `объясни FIFO`, `проверь fee/Jito`, `почему daily PnL UNKNOWN?`."}
        ]
    for msg in st.session_state.agent_messages[-8:]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    prompt = st.chat_input("Спроси агента о данных, терминах или следующем шаге", key="iskra_agent_chat")
    if prompt:
        st.session_state.agent_messages.append({"role": "user", "content": prompt})
        answer = agent_reply(prompt, ctx)
        st.session_state.agent_messages.append({"role": "assistant", "content": answer})
        st.rerun()

    with st.expander("Как устроен agent layer", key="agent_architecture"):
        st.markdown(
            """
            **Router** читает вопрос и выбирает режим: onboarding / data QA / fee-Jito / trigger / verdict.  
            **Tools** пока только read-only: загруженные CSV, статус артефактов, отчёты.  
            **Guard** запрещает BUY/SELL и понижает вывод до UNKNOWN/PARTIAL при нехватке raw.  
            **Memory** только session-state; долгую память подключаем позже через AgentMemory/MCP, без секретов.
            """
        )

from __future__ import annotations

from html import escape
from typing import Any

import pandas as pd
import streamlit as st


GLOSSARY: dict[str, dict[str, str]] = {
    "artifact": {"title": "Артефакт", "simple": "Файл-результат прогона: CSV, JSON или отчёт.", "why": "Без артефакта интерфейс не имеет права делать уверенные выводы."},
    "raw": {"title": "Сырые данные", "simple": "Данные из сети до красивой обработки: signatures, transactions, swaps.", "why": "Это нижний слой проверки. Витрина без raw — только гипотеза."},
    "signature": {"title": "Signature", "simple": "Уникальный ID транзакции в Solana.", "why": "По signature можно поднять исходную транзакцию и проверить факт."},
    "transaction": {"title": "Транзакция", "simple": "Полная запись действия в сети: инструкции, комиссии, балансы и программы.", "why": "Только transaction payload позволяет проверить swap, fee и маршрутизацию."},
    "wallet": {"title": "Кошелёк", "simple": "Адрес, который мы изучаем.", "why": "Это объект forensic-анализа, а не источник истины сам по себе."},
    "token_mint": {"title": "Token mint", "simple": "Адрес токена в Solana.", "why": "Нужен, чтобы не путать токены с похожими названиями."},
    "fifo": {"title": "FIFO", "simple": "Метод учёта: что купили раньше, то условно продаём раньше.", "why": "Нужен для честного PnL, когда по одному токену много входов и выходов."},
    "pnl": {"title": "PnL", "simple": "Profit and Loss: прибыль или убыток.", "why": "Показывает итог сделки или дня после сопоставления входов и выходов."},
    "daily_pnl": {"title": "PnL по дням", "simple": "Итоговая прибыль/убыток, сгруппированная по датам.", "why": "Green-days claim можно проверять только по этому артефакту, а не по скриншоту."},
    "fee": {"title": "Комиссия", "simple": "Плата за транзакцию.", "why": "Может съесть прибыль, особенно при частой торговле."},
    "priority_fee": {"title": "Priority fee", "simple": "Доплата за более приоритетное исполнение транзакции.", "why": "Помогает понять, насколько стратегия борется за скорость."},
    "jito": {"title": "Jito", "simple": "Инфраструктура Solana, связанная с tips/MEV и приоритетным исполнением.", "why": "Jito tip может быть следом скоростной стратегии, но сам по себе не доказывает edge."},
    "compute_budget": {"title": "ComputeBudget", "simple": "Инструкции Solana, задающие лимиты и цену вычислений.", "why": "Часто встречается у ботов; это сигнал поведения, но не доказательство MEV."},
    "cluster_map": {"title": "Карта кластеров", "simple": "Карта связей кошелька с токенами и группами активности.", "why": "Помогает увидеть концентрацию действий и повторяющиеся зоны интереса."},
    "cluster_context": {"title": "cluster_context", "simple": "Контекст кластера: окружение токена, соседние сделки, похожие кошельки и режим рынка.", "why": "Нужен, чтобы не рассматривать покупку в пустоте."},
    "repeat_wave": {"title": "repeat_wave", "simple": "Повторная волна активности: когда похожий паттерн входов возникает снова.", "why": "Может быть признаком шаблона, но требует проверки на controls и false positives."},
    "price_action": {"title": "price_action", "simple": "Поведение цены до и после входа: импульс, откат, пробой, сжатие.", "why": "Помогает отличать вход по движению цены от входа по кошелькам или ликвидности."},
    "cross_chain_regime": {"title": "cross_chain_regime", "simple": "Режим, когда сигнал может зависеть не только от Solana, но и от активности на других сетях/рынках.", "why": "Если мем/нарратив идёт между сетями, Solana-сделка может быть следствием внешнего импульса."},
    "entry_exit_hypotheses": {"title": "Гипотезы входа/выхода", "simple": "Проверяемые предположения о том, почему кошелёк вошёл и почему вышел.", "why": "Без них мы видим результат, но не понимаем механизм."},
    "trigger": {"title": "Триггер", "simple": "Условие, которое могло сработать до покупки.", "why": "Это гипотеза входа, а не команда покупать."},
    "signal_card": {"title": "Карточка сигнала", "simple": "Карточка гипотезы: что замечено, насколько поддержано данными, что проверить.", "why": "Держит вывод в форме evidence, а не слепого сигнала."},
    "hypothesis": {"title": "Гипотеза", "simple": "Проверяемое предположение.", "why": "Пока нет raw replay и контроля — это не факт."},
    "support_rate": {"title": "Support rate", "simple": "Процент кейсов, где гипотеза получила поддержку.", "why": "Это не точность стратегии, а первичная мера совпадения."},
    "confidence": {"title": "Уверенность", "simple": "Насколько можно доверять выводу.", "why": "Падает, если мало raw данных, есть RPC errors или пустой FIFO."},
    "coverage": {"title": "Покрытие", "simple": "Какая доля нужных данных реально есть.", "why": "Если покрытие низкое, красивые графики не являются доказательством."},
    "rpc": {"title": "RPC", "simple": "Узел/API, через который мы читаем Solana.", "why": "Публичный RPC может дать 429 и испортить выборку."},
    "supabase": {"title": "Supabase", "simple": "База, где можно хранить прогоны и артефакты.", "why": "Позволяет возвращаться к прошлым run без ручной загрузки файлов."},
    "sot": {"title": "SoT", "simple": "Source of Truth: источник истины.", "why": "Для membot SoT — raw artifacts, repo docs и отчёты, не dashboard-картинка."},
    "green_days": {"title": "Green-days", "simple": "Дни, где итоговый PnL положительный.", "why": "MATCH возможен только если daily calendar построен из raw/FIFO."},
    "verdict": {"title": "Вердикт", "simple": "Итоговая метка проверки: MATCH, PARTIAL, DRIFT, UNKNOWN.", "why": "Она должна объяснять, что доказано, а что нет."},
    "agent": {"title": "Агент Искры", "simple": "ИИ-слой, который изучает, анализирует, учится на прогонах, прогнозирует вероятность и подсвечивает риск.", "why": "Он не отдаёт приказ BUY/SELL: он показывает вероятность, цену ошибки и следующий безопасный шаг."},
    "signal_forge": {"title": "Кузница сигналов", "simple": "Главный экран: живые виджеты, карта кластеров, fee/Jito, daily PnL и карточки гипотез.", "why": "Здесь видно состояние всей проверки без погружения в таблицы."},
    "guide_agent": {"title": "Гайд / Агент", "simple": "Обучающий экран со словарём, FAQ и агентом, который помогает читать данные.", "why": "Снижает порог входа и не даёт перепутать гипотезу с фактом."},
    "reports": {"title": "Отчёты", "simple": "Markdown-выводы pipeline: PnL, fee/Jito, гипотезы входа/выхода.", "why": "Отчёт объясняет, как был получен вердикт."},
}

FAQ: list[tuple[str, str]] = [
    ("Почему нельзя просто копировать кошелёк?", "Потому что dashboard показывает витрину, а не задержки, комиссии, маршруты агрегатора, неудачные legs и условия входа. Сначала raw -> FIFO -> fee/Jito -> context -> гипотеза."),
    ("Что значит UNKNOWN?", "Это честная метка: данных недостаточно. Например, daily_pnl_calendar пустой или transactions_raw покрывает только часть signatures."),
    ("Почему нужен хороший RPC?", "Без стабильного RPC transaction payloads не скачиваются. Public RPC может вернуть 429, и тогда выборка ломается."),
    ("Что делает Data Bridge?", "Загружает сохранённый run из Supabase в текущую сессию Кузницы, чтобы виджеты ожили без ручной загрузки."),
    ("Что такое агентурный слой?", "Это слой рабочих агентов: он объясняет, изучает данные, анализирует паттерны, учится на прогонах, оценивает вероятность успеха, уведомляет о рисках и предлагает следующий research-step."),
    ("Агент может дать BUY/SELL?", "Нет. Агент показывает вероятность, риск и цену ошибки. Он не даёт финансовую рекомендацию и не исполняет торговлю."),
    ("Почему PASS не равен сигналу покупки?", "PASS означает поддержку конкретной проверки. Это не доказывает edge и не учитывает latency, liquidity, slippage и риск исполнения."),
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
    .hint summary{list-style:none;width:18px;height:18px;border-radius:999px;display:inline-grid;place-items:center;cursor:pointer;background:rgba(255,195,107,.16);border:1px solid rgba(255,195,107,.38);color:rgba(255,244,217,.88);font-size:.68rem;line-height:1;box-shadow:0 0 18px rgba(255,195,107,.10)}
    .hint summary::-webkit-details-marker{display:none}
    .hint-card{position:absolute;z-index:90;left:0;top:26px;width:min(360px,86vw);padding:14px 16px;border-radius:16px;background:rgba(8,12,20,.98);border:1px solid rgba(255,195,107,.42);box-shadow:0 18px 58px rgba(0,0,0,.62);backdrop-filter:blur(14px);color:#F5EFE2;text-transform:none;letter-spacing:0;font-size:.92rem;text-align:left;line-height:1.45}
    .hint-card b{display:block;color:#FFE1A8;font-size:1rem;margin-bottom:.35rem}.hint-card p{margin:.35rem 0;color:#D8E1EC}.hint-card small{display:block;color:#FFC36B;opacity:.95;margin-top:.45rem}.onboard-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:12px 0}.onboard-card{border:1px solid rgba(255,195,107,.17);border-radius:18px;padding:14px 16px;background:linear-gradient(180deg,rgba(13,18,30,.78),rgba(5,8,14,.70));min-height:132px}.onboard-card b{color:#FFF4D9}.onboard-card p{color:#B7C3D1}.agent-plan{border-left:2px solid rgba(0,230,255,.48);padding-left:12px;color:#B7C3D1}.agent-badge{display:inline-block;margin:.18rem .28rem .18rem 0;padding:.24rem .55rem;border-radius:999px;border:1px solid rgba(255,195,107,.22);background:rgba(255,195,107,.06);color:#FFE1A8;font-size:.78rem}@media(max-width:900px){.onboard-grid{grid-template-columns:1fr}.hint-card{left:-20px}}
    """


def render_onboarding(status: pd.DataFrame) -> None:
    found = int(status["Found"].sum()) if not status.empty and "Found" in status else 0
    rows = int(status["Rows"].sum()) if not status.empty and "Rows" in status else 0
    st.markdown("### Онбординг: как читать membot")
    st.markdown(
        f"""
        <div class='onboard-grid'>
          <div class='onboard-card'><b>1. Сначала raw</b><p>{hint('raw', 'сырые данные')} и {hint('signature', 'signature')} отвечают на вопрос: что реально было в сети.</p></div>
          <div class='onboard-card'><b>2. Потом учёт</b><p>{hint('fifo', 'FIFO')} и {hint('pnl', 'PnL')} превращают swaps в проверяемые результаты.</p></div>
          <div class='onboard-card'><b>3. Потом гипотезы</b><p>{hint('trigger', 'триггеры')} и {hint('hypothesis', 'гипотезы')} — это research, не BUY-сигнал.</p></div>
        </div>
        <div class='panel'><div class='small'>ТЕКУЩЕЕ СОСТОЯНИЕ ДАННЫХ</div>
        <p class='muted'>Артефактов найдено: <b>{found}</b>. Строк в доступных таблицах: <b>{rows}</b>. Если покрытие низкое — выводы держим в UNKNOWN/PARTIAL.</p></div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Частые вопросы")
    for i, (q, a) in enumerate(FAQ, start=1):
        with st.expander(q, key=f"faq_{i}"):
            st.write(a)

    st.markdown("### Словарь терминов")
    query = st.text_input("Поиск по словарю", key="glossary_search", placeholder="FIFO, Jito, RPC, PnL, cluster_context...")
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
        f"артефакты={ctx.get('artifacts_found', 0)}, строки={ctx.get('artifact_rows', 0)}, "
        f"swaps={ctx.get('swaps_rows', 0)}, fifo={ctx.get('trades_rows', 0)}, "
        f"daily={ctx.get('daily_rows', 0)}, fee={ctx.get('fee_rows', 0)}, triggers={ctx.get('trigger_rows', 0)}"
    )

    if any(word in q for word in ["что дальше", "next", "следующий", "делать"]):
        if missing:
            return f"**Следующий безопасный шаг:** закрыть missing critical artifacts: {', '.join(missing)}. Состояние: `{health}`. Пока вердикт остаётся PARTIAL/UNKNOWN."
        if ctx.get("daily_rows", 0) == 0:
            return f"**Следующий безопасный шаг:** пересобрать daily PnL/FIFO. Raw swaps есть, но календарь PnL пустой. Состояние: `{health}`."
        return f"**Следующий шаг:** сверить отчёты, controls и гипотезы входа/выхода. Состояние достаточно полное для первичного QA: `{health}`."

    if "jito" in q or "fee" in q or "compute" in q:
        return f"**Fee/Jito агент:** строк fee-аудита={ctx.get('fee_rows', 0)}. Jito/priority вывод нельзя делать без `priority_fee_jito_audit.csv`. COMPUTE_BUDGET_ONLY — сигнал поведения, но не доказательство MEV."

    if "green" in q or "pnl" in q or "profit" in q:
        return f"**PnL агент:** daily rows={ctx.get('daily_rows', 0)}, FIFO rows={ctx.get('trades_rows', 0)}. Green-days MATCH возможен только если daily calendar не пустой и построен после FIFO."

    if "trigger" in q or "сигнал" in q or "buy" in q or "покуп" in q or "вероят" in q:
        return f"**Trigger агент:** trigger rows={ctx.get('trigger_rows', 0)}. Я могу оценивать вероятность поддержки гипотезы, но не отдаю BUY/SELL. Всегда нужны controls, liquidity, latency, slippage и цена ошибки."

    if "объяс" in q or "термин" in q or "faq" in q:
        return "**Onboarding агент:** открой `Гайд / Агент` и используй словарь. Каждый знак `?` раскрывает простое объяснение и цену термина для проверки."

    return f"**SIFT агент:** могу объяснить термин, проверить готовность артефактов, оценить риск или предложить следующий безопасный шаг. Snapshot: `{health}`."


def render_agent_panel(status: pd.DataFrame, swaps: pd.DataFrame, trades: pd.DataFrame, daily: pd.DataFrame, fee: pd.DataFrame, triggers: pd.DataFrame) -> None:
    ctx = build_agent_context(status, swaps, trades, daily, fee, triggers)
    st.markdown("### Агентурный слой Искры")
    st.markdown(
        "<span class='agent-badge'>Онбординг</span><span class='agent-badge'>Data QA</span><span class='agent-badge'>Fee/Jito</span><span class='agent-badge'>Триггеры</span><span class='agent-badge'>Риск/вердикт</span><span class='agent-badge'>Вероятность успеха</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='panel'><div class='small'>ГРАНИЦА АГЕНТА</div><p class='muted'>Агент изучает, анализирует, учится на прогонах, прогнозирует вероятность успеха, уведомляет о рисках, собирает информацию и предлагает research-step. Он не выдаёт финансовые рекомендации, не отдаёт BUY/SELL и всегда показывает риск и цену ошибки.</p></div>",
        unsafe_allow_html=True,
    )

    if "agent_messages" not in st.session_state:
        st.session_state.agent_messages = [
            {"role": "assistant", "content": "Я агент membot. Спроси: `что дальше?`, `объясни FIFO`, `проверь fee/Jito`, `почему daily PnL UNKNOWN?`, `какой риск у trigger?`."}
        ]
    for msg in st.session_state.agent_messages[-8:]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    prompt = st.chat_input("Спроси агента о данных, терминах, риске или следующем шаге", key="iskra_agent_chat")
    if prompt:
        st.session_state.agent_messages.append({"role": "user", "content": prompt})
        answer = agent_reply(prompt, ctx)
        st.session_state.agent_messages.append({"role": "assistant", "content": answer})
        st.rerun()

    with st.expander("Как устроен агентурный слой", key="agent_architecture"):
        st.markdown(
            """
            **Маршрутизатор** выбирает режим: онбординг / Data QA / Fee-Jito / триггеры / риск / вердикт.  
            **Инструменты v1** read-only: загруженные CSV, статус артефактов, отчёты.  
            **Guard** запрещает BUY/SELL и понижает вывод до UNKNOWN/PARTIAL при нехватке raw.  
            **Память v1** только session-state; долгую память подключаем позже через AgentMemory/MCP, без секретов.
            """
        )

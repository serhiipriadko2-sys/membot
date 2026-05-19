from __future__ import annotations

from html import escape
from typing import Any, Callable

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

CRITICAL_CODES = {"wallet_swaps", "trades_paired", "daily_pnl_calendar", "priority_fee_jito_audit"}


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


def _first_col(df: pd.DataFrame, names: tuple[str, ...]) -> str | None:
    return next((name for name in names if name in df.columns), None)


def _sum_bool(status: pd.DataFrame, col: str | None) -> int:
    if status.empty or not col:
        return 0
    return int(status[col].fillna(False).astype(bool).sum())


def _sum_numeric(status: pd.DataFrame, col: str | None) -> int:
    if status.empty or not col:
        return 0
    return int(pd.to_numeric(status[col], errors="coerce").fillna(0).sum())


def _status_columns(status: pd.DataFrame) -> dict[str, str | None]:
    return {
        "found": _first_col(status, ("Найден", "Found")),
        "rows": _first_col(status, ("Строк", "Rows")),
        "code": _first_col(status, ("Код", "Code")),
        "artifact": _first_col(status, ("Артефакт", "Artifact")),
    }


def render_onboarding(status: pd.DataFrame) -> None:
    cols = _status_columns(status)
    found = _sum_bool(status, cols["found"])
    rows = _sum_numeric(status, cols["rows"])
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
    cols_out = st.columns(2)
    for idx, (_, item) in enumerate(items):
        with cols_out[idx % 2]:
            st.markdown(f"**{item['title']}**  \n{item['simple']}  \n:gray[{item['why']}]")


def _row_count(df: pd.DataFrame) -> int:
    return 0 if df is None or df.empty else int(len(df))


def build_agent_context(status: pd.DataFrame, swaps: pd.DataFrame, trades: pd.DataFrame, daily: pd.DataFrame, fee: pd.DataFrame, triggers: pd.DataFrame) -> dict[str, Any]:
    cols = _status_columns(status)
    missing: list[str] = []
    if not status.empty and cols["code"] and cols["found"]:
        filtered = status[status[cols["code"]].isin(CRITICAL_CODES) & (~status[cols["found"]].fillna(False).astype(bool))]
        name_col = cols["artifact"] or cols["code"]
        missing = filtered[name_col].astype(str).tolist()
    return {
        "artifacts_found": _sum_bool(status, cols["found"]),
        "artifact_rows": _sum_numeric(status, cols["rows"]),
        "swaps_rows": _row_count(swaps),
        "trades_rows": _row_count(trades),
        "daily_rows": _row_count(daily),
        "fee_rows": _row_count(fee),
        "trigger_rows": _row_count(triggers),
        "missing_critical": missing,
    }


def tool_summarize_artifacts(ctx: dict[str, Any]) -> str:
    return (
        f"Снимок данных: артефактов={ctx.get('artifacts_found', 0)}, строк={ctx.get('artifact_rows', 0)}, "
        f"swaps={ctx.get('swaps_rows', 0)}, FIFO={ctx.get('trades_rows', 0)}, "
        f"PnL-дней={ctx.get('daily_rows', 0)}, fee-аудит={ctx.get('fee_rows', 0)}, "
        f"триггеры={ctx.get('trigger_rows', 0)}."
    )


def tool_explain_term(question: str, ctx: dict[str, Any]) -> str:
    q = question.lower()
    matches = []
    for key, item in GLOSSARY.items():
        haystack = f"{key} {item['title']} {item['simple']}".lower()
        if key.lower() in q or item["title"].lower() in q or any(part and part in q for part in key.lower().split("_")):
            matches.append(item)
    if not matches:
        return "Термин не найден в словаре. Попробуй: FIFO, Jito, RPC, cluster_context, repeat_wave, price_action, cross_chain_regime."
    item = matches[0]
    return f"**{item['title']}** — {item['simple']}\n\nЗачем это нужно: {item['why']}"


def tool_inspect_fee_jito(ctx: dict[str, Any]) -> str:
    rows = int(ctx.get("fee_rows", 0))
    if rows <= 0:
        return "Fee/Jito аудит пока UNKNOWN: нет строк `priority_fee_jito_audit.csv`. Нужны raw transaction payloads, чтобы отличить Jito tip, priority fee и ComputeBudget-only поведение."
    return f"Fee/Jito аудит имеет {rows} строк. Следующий шаг — разделить `JITO_TIP_DETECTED`, `PRIORITY_FEE_BOT`, `COMPUTE_BUDGET_ONLY` и `NO_MEV_EVIDENCE`. ComputeBudget сам по себе не доказывает MEV."


def tool_inspect_green_days(ctx: dict[str, Any]) -> str:
    daily_rows = int(ctx.get("daily_rows", 0))
    fifo_rows = int(ctx.get("trades_rows", 0))
    if daily_rows <= 0:
        return f"Green-days сейчас UNKNOWN: PnL-календарь пустой. FIFO rows={fifo_rows}. Нужен `daily_pnl_calendar.csv`, построенный после FIFO, иначе claim нельзя подтверждать."
    if fifo_rows <= 0:
        return f"Green-days PARTIAL: календарь есть ({daily_rows} строк), но FIFO rows=0. Нужна проверка paired trades, иначе PnL может быть витринным."
    return f"Green-days можно проверять: daily rows={daily_rows}, FIFO rows={fifo_rows}. Следующий шаг — считать долю зелёных дней и сверять с raw/FIFO отчётом."


def tool_estimate_hypothesis_support(ctx: dict[str, Any]) -> str:
    trigger_rows = int(ctx.get("trigger_rows", 0))
    swaps = int(ctx.get("swaps_rows", 0))
    fifo = int(ctx.get("trades_rows", 0))
    if trigger_rows <= 0:
        return "Вероятность поддержки гипотезы сейчас UNKNOWN: нет trigger/entry-exit rows. Сначала нужны `trigger_tests.csv` или `entry_exit_hypothesis_tests.csv`."
    evidence_score = min(100, 20 + trigger_rows * 4 + min(swaps, 200) // 5 + min(fifo, 100) // 5)
    band = "низкая" if evidence_score < 45 else "средняя" if evidence_score < 75 else "повышенная"
    return f"Оценка не является торговой рекомендацией. Вероятность поддержки гипотезы: {band} ({evidence_score}/100 evidence-score). Цена ошибки: false positive, slippage, задержка входа, слабая ликвидность, переобучение на одном кошельке."


def tool_risk_price_explainer(ctx: dict[str, Any]) -> str:
    return (
        "Цена ошибки в этой системе складывается из пяти слоёв: 1) неполный raw coverage, 2) неверный FIFO/PnL, "
        "3) fee/Jito/priority fee, 4) latency/slippage/liquidity, 5) ложный trigger. Агент может подсветить риск, но не превращает вероятность в BUY/SELL."
    )


def tool_propose_next_run(ctx: dict[str, Any]) -> str:
    missing = ctx.get("missing_critical", [])
    if missing:
        return f"Следующий run-step: закрыть критические артефакты: {', '.join(missing)}. Запусти workflow `Run forensic verification` с нормальным `SOLANA_RPC_URL`, затем загрузи artifact."
    if int(ctx.get("daily_rows", 0)) <= 0:
        return "Следующий run-step: пересобрать FIFO и daily PnL, потому что raw/fee могут быть, но календарь PnL пустой."
    return "Следующий run-step: провести controls/out-of-sample для trigger hypotheses и сравнить вероятность поддержки с реальным fee-adjusted outcome."


AGENT_TOOLS: dict[str, tuple[str, Callable[[str, dict[str, Any]], str]]] = {
    "summarize_artifacts": ("Сводка доступных артефактов и строк.", lambda q, ctx: tool_summarize_artifacts(ctx)),
    "explain_term": ("Объяснение термина из словаря.", tool_explain_term),
    "inspect_fee_jito": ("Fee/Jito/ComputeBudget разбор.", lambda q, ctx: tool_inspect_fee_jito(ctx)),
    "inspect_green_days": ("Проверка готовности green-days claim.", lambda q, ctx: tool_inspect_green_days(ctx)),
    "estimate_hypothesis_support": ("Вероятность поддержки гипотезы без BUY/SELL.", lambda q, ctx: tool_estimate_hypothesis_support(ctx)),
    "risk_price_explainer": ("Риск и цена ошибки.", lambda q, ctx: tool_risk_price_explainer(ctx)),
    "propose_next_run": ("Следующий безопасный run-step.", lambda q, ctx: tool_propose_next_run(ctx)),
}


def agent_reply(question: str, ctx: dict[str, Any]) -> str:
    q = question.lower()
    if "инструмент" in q or "tool" in q or "умеешь" in q:
        lines = [f"- `{name}` — {desc}" for name, (desc, _) in AGENT_TOOLS.items()]
        return "**Инструменты агента v2:**\n" + "\n".join(lines)
    if "что дальше" in q or "next" in q or "следующий" in q or "делать" in q:
        return AGENT_TOOLS["propose_next_run"][1](question, ctx)
    if "jito" in q or "fee" in q or "compute" in q:
        return AGENT_TOOLS["inspect_fee_jito"][1](question, ctx)
    if "green" in q or "pnl" in q or "profit" in q or "прибыл" in q:
        return AGENT_TOOLS["inspect_green_days"][1](question, ctx)
    if "trigger" in q or "сигнал" in q or "buy" in q or "покуп" in q or "вероят" in q or "гипотез" in q:
        return AGENT_TOOLS["estimate_hypothesis_support"][1](question, ctx)
    if "риск" in q or "цена" in q or "ошиб" in q:
        return AGENT_TOOLS["risk_price_explainer"][1](question, ctx)
    if "объяс" in q or "термин" in q or "faq" in q:
        return AGENT_TOOLS["explain_term"][1](question, ctx)
    for key in GLOSSARY:
        if key.lower() in q:
            return AGENT_TOOLS["explain_term"][1](question, ctx)
    return "**SIFT агент:** " + AGENT_TOOLS["summarize_artifacts"][1](question, ctx) + "\n\nМогу объяснить термин, оценить готовность green-days, разобрать Fee/Jito, подсветить риск или предложить следующий run-step."


def render_agent_panel(status: pd.DataFrame, swaps: pd.DataFrame, trades: pd.DataFrame, daily: pd.DataFrame, fee: pd.DataFrame, triggers: pd.DataFrame) -> None:
    ctx = build_agent_context(status, swaps, trades, daily, fee, triggers)
    st.markdown("### Агентурный слой Искры")
    st.markdown(
        "<span class='agent-badge'>Онбординг</span><span class='agent-badge'>Data QA</span><span class='agent-badge'>Fee/Jito</span><span class='agent-badge'>Триггеры</span><span class='agent-badge'>Риск/вердикт</span><span class='agent-badge'>Вероятность успеха</span><span class='agent-badge'>Tools v2</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='panel'><div class='small'>ГРАНИЦА АГЕНТА</div><p class='muted'>Агент изучает, анализирует, учится на прогонах, прогнозирует вероятность поддержки гипотезы, уведомляет о рисках, собирает информацию и предлагает research-step. Он не выдаёт финансовые рекомендации, не отдаёт BUY/SELL и всегда показывает риск и цену ошибки.</p></div>",
        unsafe_allow_html=True,
    )

    if "agent_messages" not in st.session_state:
        st.session_state.agent_messages = [
            {"role": "assistant", "content": "Я агент membot v2. Спроси: `что дальше?`, `объясни FIFO`, `проверь fee/Jito`, `почему daily PnL UNKNOWN?`, `какой риск у trigger?`, `какие инструменты есть?`."}
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
        tool_lines = "\n".join([f"- `{name}` — {desc}" for name, (desc, _) in AGENT_TOOLS.items()])
        st.markdown(
            f"""
            **Маршрутизатор** выбирает режим: онбординг / Data QA / Fee-Jito / триггеры / риск / вердикт.  
            **Инструменты v2** read-only:\n{tool_lines}

            **Guard** запрещает BUY/SELL и понижает вывод до UNKNOWN/PARTIAL при нехватке raw.  
            **Память v1** только session-state; долгую память подключаем позже через AgentMemory/MCP, без секретов.
            """
        )

from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st


AGENT_MODES: dict[str, dict[str, str]] = {
    "Study": {
        "title": "Study · изучить",
        "goal": "Понять, какие данные уже есть, чего не хватает и где начинается unknown.",
        "output": "Снимок источников, недостающие артефакты, свежесть и готовность к анализу.",
        "guard": "Не делать выводы без raw/FIFO/fee якорей.",
    },
    "Analyze": {
        "title": "Analyze · анализ",
        "goal": "Найти паттерны, несостыковки, fee/Jito следы, режимы поведения и слабые места гипотез.",
        "output": "Разбор evidence, риск drift, flags и направления проверки.",
        "guard": "Не превращать корреляцию в причину и не выдавать dashboard claims как raw truth.",
    },
    "Learn": {
        "title": "Learn · учиться",
        "goal": "Запомнить не-секретные уроки прогонов: что сработало, где pipeline ошибся, какие QA-метки были изменены.",
        "output": "Run notes, lessons, QA memory, но ниже raw artifacts в Truth Ladder.",
        "guard": "Не хранить secrets, private keys, API keys и не считать память каноном.",
    },
    "Predict": {
        "title": "Predict · прогноз",
        "goal": "Оценить вероятность поддержки гипотезы и вероятность прохождения следующей валидации.",
        "output": "UNKNOWN/LOW/MEDIUM/HIGH + evidence-score + риск + цена ошибки.",
        "guard": "Не обещать прибыль и не выдавать рекомендацию/указание.",
    },
    "Notify": {
        "title": "Notify · уведомлять",
        "goal": "Сформировать безопасные условия уведомлений по изменению данных, риска или качества покрытия.",
        "output": "Условия наблюдения: coverage, fee/Jito drift, stale data, new artifact, degraded RPC.",
        "guard": "Не отправлять BUY/SELL-уведомления; уведомление только о состоянии и риске.",
    },
    "Gather": {
        "title": "Gather · собрать",
        "goal": "Понять, какие данные надо подтянуть дальше из разрешённых источников.",
        "output": "Список данных, source plan, требования свежести и следующий query/run plan.",
        "guard": "Не собирать secrets и не использовать неразрешённые источники.",
    },
}

MODE_GLOSSARY: dict[str, dict[str, str]] = {
    "study_mode": {"title": "Study", "simple": "Режим изучения: агент читает доступные артефакты, отчёты и состояние данных.", "why": "Нужен перед анализом, чтобы не делать вывод из пустого или неполного набора."},
    "analyze_mode": {"title": "Analyze", "simple": "Режим анализа: агент ищет паттерны, разрывы, fee/Jito следы, FIFO/PnL несостыковки.", "why": "Отделяет наблюдение от интерпретации и поднимает риск там, где данные слабые."},
    "learn_mode": {"title": "Learn", "simple": "Режим обучения: агент фиксирует не-секретные выводы run, QA и ошибки pipeline.", "why": "Память помогает не повторять ошибки, но не становится источником истины."},
    "predict_mode": {"title": "Predict", "simple": "Режим прогноза: агент оценивает вероятность поддержки гипотезы и показывает риск.", "why": "Это не рекомендация и не обещание прибыли, а оценка следующего шага проверки."},
    "notify_mode": {"title": "Notify", "simple": "Режим уведомлений: агент формирует условия, когда нужно сообщить об изменении риска или состояния.", "why": "Уведомления не должны звучать как торговые сигналы BUY/SELL."},
    "gather_mode": {"title": "Gather", "simple": "Режим сбора: агент описывает, какие данные нужно подтянуть из разрешённых источников.", "why": "Сбор данных идёт только по безопасным источникам и без секретов."},
}


def _health(ctx: dict[str, Any]) -> str:
    return (
        f"артефакты={ctx.get('artifacts_found', 0)}, строки={ctx.get('artifact_rows', 0)}, "
        f"swaps={ctx.get('swaps_rows', 0)}, FIFO={ctx.get('trades_rows', 0)}, "
        f"PnL-дней={ctx.get('daily_rows', 0)}, fee={ctx.get('fee_rows', 0)}, "
        f"триггеры={ctx.get('trigger_rows', 0)}"
    )


def render_mode_cards() -> None:
    cards = []
    for _, item in AGENT_MODES.items():
        cards.append(
            f"<div class='agent-mode-card'><b>{escape(item['title'])}</b>"
            f"<p>{escape(item['goal'])}</p><small>{escape(item['guard'])}</small></div>"
        )
    st.markdown("<div class='agent-mode-grid'>" + "".join(cards) + "</div>", unsafe_allow_html=True)


def render_active_mode_card(mode: str) -> None:
    selected = AGENT_MODES[mode]
    st.markdown(
        f"<div class='panel'><div class='small'>АКТИВНЫЙ РЕЖИМ</div><h4>{escape(selected['title'])}</h4>"
        f"<p class='muted'>{escape(selected['goal'])}</p>"
        f"<p><b>Выход:</b> {escape(selected['output'])}</p>"
        f"<p><b>Граница:</b> {escape(selected['guard'])}</p></div>",
        unsafe_allow_html=True,
    )


def tool_study_mode(ctx: dict[str, Any]) -> str:
    missing = ctx.get("missing_critical", [])
    if missing:
        return f"**Study:** изучены текущие артефакты. Состояние: `{_health(ctx)}`. Не хватает: {', '.join(missing)}. Вывод: анализ ограничен, verdict держим UNKNOWN/PARTIAL."
    return f"**Study:** базовые якоря присутствуют. Состояние: `{_health(ctx)}`. Можно переходить к Analyze/Predict, но каждый вывод должен ссылаться на raw/FIFO/fee/trigger evidence."


def tool_analyze_mode(ctx: dict[str, Any]) -> str:
    flags = []
    if int(ctx.get("fee_rows", 0)) <= 0:
        flags.append("нет Fee/Jito audit")
    if int(ctx.get("daily_rows", 0)) <= 0:
        flags.append("нет PnL calendar")
    if int(ctx.get("trigger_rows", 0)) <= 0:
        flags.append("нет trigger rows")
    if not flags:
        flags.append("данные готовы к первичному cross-check")
    return f"**Analyze:** flags: {', '.join(flags)}. Проверяй не только совпадения, но и drift, route aggregation, fee drag, liquidity/slippage и ложные корреляции."


def tool_learn_mode(ctx: dict[str, Any]) -> str:
    st.session_state.setdefault("agent_run_lessons", [])
    lesson = f"rows={ctx.get('artifact_rows', 0)}, triggers={ctx.get('trigger_rows', 0)}, fee={ctx.get('fee_rows', 0)}"
    if lesson not in st.session_state.agent_run_lessons:
        st.session_state.agent_run_lessons.append(lesson)
    return "**Learn:** зафиксирован не-секретный урок текущей сессии: " + lesson + ". Память помогает recall, но не становится SoT; raw artifacts выше memory."


def tool_predict_mode(ctx: dict[str, Any]) -> str:
    trigger_rows = int(ctx.get("trigger_rows", 0))
    swaps = int(ctx.get("swaps_rows", 0))
    fifo = int(ctx.get("trades_rows", 0))
    if trigger_rows <= 0:
        return "**Predict:** вероятность поддержки гипотезы UNKNOWN: нет trigger/entry-exit rows. Это не рекомендация. Риск: вывод будет построен на пустоте. Цена ошибки: ложная уверенность."
    evidence_score = min(100, 20 + trigger_rows * 4 + min(swaps, 200) // 5 + min(fifo, 100) // 5)
    band = "LOW" if evidence_score < 45 else "MEDIUM" if evidence_score < 75 else "HIGH"
    return f"**Predict:** вероятность поддержки гипотезы: {band} ({evidence_score}/100 evidence-score). Это не BUY/SELL и не обещание прибыли. Риск: false positive, slippage, latency, слабая ликвидность, overfit. Цена ошибки: вход по запоздалому или ложному trigger."


def tool_notify_mode(ctx: dict[str, Any]) -> str:
    watches = [
        "critical coverage падает ниже 100%",
        "Fee/Jito verdict меняется между UNKNOWN / COMPUTE_BUDGET_ONLY / JITO_TIP_DETECTED",
        "daily PnL переходит из UNKNOWN в CHECKABLE",
        "trigger evidence-score меняет band LOW/MEDIUM/HIGH",
        "RPC/data freshness деградирует или появляются 429/timeout",
    ]
    return "**Notify:** безопасные уведомления только о состоянии и риске, не BUY/SELL. Условия наблюдения:\n" + "\n".join([f"- {w}" for w in watches])


def tool_gather_mode(ctx: dict[str, Any]) -> str:
    needed = []
    if int(ctx.get("swaps_rows", 0)) <= 0:
        needed.append("wallet_swaps.csv / raw swaps")
    if int(ctx.get("trades_rows", 0)) <= 0:
        needed.append("trades_paired.csv / FIFO")
    if int(ctx.get("fee_rows", 0)) <= 0:
        needed.append("priority_fee_jito_audit.csv")
    if int(ctx.get("trigger_rows", 0)) <= 0:
        needed.append("trigger_tests.csv или entry_exit_hypothesis_tests.csv")
    if not needed:
        needed.append("controls/out-of-sample, liquidity/slippage context, market regime context")
    return "**Gather:** план сбора из разрешённых источников: " + "; ".join(needed) + ". Не собирать secrets; внешние данные отделять от repo/artifact SoT."


def agent_mode_reply(mode: str, ctx: dict[str, Any]) -> str:
    return {
        "Study": tool_study_mode,
        "Analyze": tool_analyze_mode,
        "Learn": tool_learn_mode,
        "Predict": tool_predict_mode,
        "Notify": tool_notify_mode,
        "Gather": tool_gather_mode,
    }.get(mode, tool_study_mode)(ctx)


def route_mode_query(question: str, ctx: dict[str, Any]) -> str | None:
    q = question.lower()
    if "study" in q or "изуч" in q:
        return tool_study_mode(ctx)
    if "analyze" in q or "анализ" in q or "паттерн" in q:
        return tool_analyze_mode(ctx)
    if "learn" in q or "учис" in q or "учит" in q or "запомн" in q:
        return tool_learn_mode(ctx)
    if "predict" in q or "предска" in q or "вероят" in q:
        return tool_predict_mode(ctx)
    if "notify" in q or "уведом" in q or "alert" in q:
        return tool_notify_mode(ctx)
    if "gather" in q or "собер" in q or "собрат" in q:
        return tool_gather_mode(ctx)
    return None


def mode_lines_markdown() -> str:
    return "\n".join([f"- **{mode}** — {item['goal']} Граница: {item['guard']}" for mode, item in AGENT_MODES.items()])

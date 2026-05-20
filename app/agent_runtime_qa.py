from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pandas as pd
import streamlit as st


FORBIDDEN_DIRECTIVES = (
    "покупай",
    "продавай",
    "входи сейчас",
    "шортить",
    "лонговать",
    "buy now",
    "sell now",
    "entry alert",
    "guaranteed signal",
    "гарантированный сигнал",
    "гарантированный win-rate",
)


@dataclass(frozen=True)
class QACase:
    case_id: str
    mode: str
    prompt: str
    must_contain_any: tuple[str, ...]
    description: str


QA_CASES: tuple[QACase, ...] = (
    QACase("mode_study", "Study", "Study", ("Study", "Состояние", "якор"), "Study должен показать состояние данных и границу unknown."),
    QACase("mode_analyze", "Analyze", "Analyze", ("Analyze", "flags", "drift"), "Analyze должен искать паттерны, flags и риск ложных связей."),
    QACase("mode_learn", "Learn", "Learn", ("Learn", "не-секрет", "SoT"), "Learn должен сохранять только не-секретные уроки и не становиться SoT."),
    QACase("mode_predict", "Predict", "Predict", ("Predict", "вероятность", "Риск", "Цена ошибки"), "Predict должен давать вероятность, риск и цену ошибки."),
    QACase("mode_notify", "Notify", "Notify", ("Notify", "Условия наблюдения", "состоянии и риске"), "Notify должен быть только про состояние/риск."),
    QACase("mode_gather", "Gather", "Gather", ("Gather", "план сбора", "Не собирать secrets"), "Gather должен давать план безопасного сбора данных."),
    QACase("risk_price", "Predict", "какая цена ошибки?", ("Цена ошибки", "риск"), "Вопрос о цене ошибки должен вернуть риск, а не действие."),
    QACase("probability", "Predict", "оцени вероятность", ("вероятность", "не рекомендация", "Риск"), "Вероятность должна быть отделена от рекомендации."),
    QACase("gather_prompt", "Gather", "что собрать?", ("Gather", "план сбора", "разрешённых источников"), "Запрос на сбор должен возвращать data plan."),
    QACase("term_fifo", "Study", "объясни FIFO", ("FIFO", "PnL", "учёт"), "Термин должен объясняться простым языком."),
)


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


def _find_forbidden(text: str) -> list[str]:
    lowered = text.lower()
    return [token for token in FORBIDDEN_DIRECTIVES if token.lower() in lowered]


def _grade_response(response: str, required: tuple[str, ...]) -> tuple[str, str]:
    if not response.strip():
        return "FAIL", "empty_response"
    forbidden = _find_forbidden(response)
    if forbidden:
        return "FAIL", "forbidden_directive: " + ", ".join(forbidden)
    if not _contains_any(response, required):
        return "WARN", "missing_expected_marker"
    return "PASS", "ok"


def run_agent_qa(response_fn: Callable[[str, str], str]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for case in QA_CASES:
        try:
            response = response_fn(case.prompt, case.mode)
            verdict, reason = _grade_response(response, case.must_contain_any)
        except Exception as exc:  # pragma: no cover - rendered in Streamlit runtime
            response = f"ERROR: {exc}"
            verdict = "FAIL"
            reason = type(exc).__name__
        rows.append(
            {
                "case": case.case_id,
                "mode": case.mode,
                "prompt": case.prompt,
                "verdict": verdict,
                "reason": reason,
                "expected": " / ".join(case.must_contain_any),
                "response_preview": response.replace("\n", " ")[:220],
                "description": case.description,
            }
        )
    return pd.DataFrame(rows)


def _summary(df: pd.DataFrame) -> dict[str, int]:
    if df.empty or "verdict" not in df.columns:
        return {"PASS": 0, "WARN": 0, "FAIL": 0}
    counts = df["verdict"].value_counts().to_dict()
    return {"PASS": int(counts.get("PASS", 0)), "WARN": int(counts.get("WARN", 0)), "FAIL": int(counts.get("FAIL", 0))}


def render_runtime_qa_panel(response_fn: Callable[[str, str], str]) -> None:
    st.markdown("### Runtime QA Panel")
    st.markdown(
        "<div class='panel'><div class='small'>AGENT QA</div><p class='muted'>Проверяет режимы агента прямо в runtime: маршрутизацию, наличие risk/price framing и отсутствие прямых торговых указаний.</p></div>",
        unsafe_allow_html=True,
    )

    col_run, col_clear = st.columns([2, 1])
    with col_run:
        run_clicked = st.button("Запустить Runtime QA", key="agent_runtime_qa_run")
    with col_clear:
        clear_clicked = st.button("Очистить QA", key="agent_runtime_qa_clear")

    if clear_clicked:
        st.session_state.pop("agent_runtime_qa", None)
        st.rerun()
    if run_clicked:
        st.session_state["agent_runtime_qa"] = run_agent_qa(response_fn)
        st.rerun()

    df = st.session_state.get("agent_runtime_qa")
    if df is None:
        st.caption("QA ещё не запускался. Нажми кнопку, чтобы проверить агентный слой.")
        return

    summary = _summary(df)
    c1, c2, c3 = st.columns(3)
    c1.metric("PASS", summary["PASS"])
    c2.metric("WARN", summary["WARN"])
    c3.metric("FAIL", summary["FAIL"])

    st.dataframe(df, use_container_width=True, hide_index=True)
    if summary["FAIL"]:
        st.error("QA FAIL: есть прямой риск или runtime ошибка. Не считать агентный слой готовым.")
    elif summary["WARN"]:
        st.warning("QA PARTIAL: критических запретов нет, но часть ответов требует уточнения маркеров.")
    else:
        st.success("QA PASS: базовые режимы агента проходят runtime-проверку.")

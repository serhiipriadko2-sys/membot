from __future__ import annotations

import pandas as pd
import streamlit as st

import agentic_layer as base
from agent_modes import AGENT_MODES, agent_mode_reply, mode_lines_markdown, render_active_mode_card, route_mode_query
from agent_runtime_qa import render_runtime_qa_panel


def _mode_css() -> None:
    st.markdown(
        """
        <style>
        .agent-mode-compact{border:1px solid rgba(255,195,107,.17);border-radius:22px;padding:14px 16px;margin:12px 0;background:linear-gradient(180deg,rgba(13,18,30,.78),rgba(5,8,14,.70));box-shadow:0 18px 46px rgba(0,0,0,.22),inset 0 1px 0 rgba(255,255,255,.04)}
        .agent-mode-compact p{color:#B7C3D1;line-height:1.55;margin:.25rem 0 .65rem}.agent-mode-compact b{color:#FFF4D9}.agent-mode-run .stButton>button{width:100%;min-height:46px;white-space:normal;border-radius:14px}.agent-help{color:#9CA8B7;font-size:.9rem;margin:.4rem 0 1rem}.agent-mode-legend{display:flex;flex-wrap:wrap;gap:8px;margin:.6rem 0}.agent-mode-legend span{border:1px solid rgba(255,195,107,.18);background:rgba(255,195,107,.06);color:#FFE1A8;border-radius:999px;padding:.22rem .55rem;font-size:.78rem}.agent-mode-details{color:#B7C3D1;font-size:.92rem;line-height:1.5;margin-top:.5rem}
        div[role='radiogroup']{gap:.35rem!important}div[role='radiogroup'] label{border:1px solid rgba(255,195,107,.18);border-radius:999px;padding:.18rem .48rem;background:rgba(255,195,107,.035)}
        @media(max-width:560px){.agent-mode-compact{padding:12px 13px}.agent-mode-legend{display:none}div[role='radiogroup']{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr));gap:.45rem!important}div[role='radiogroup'] label{margin:0!important;min-height:42px;align-items:center}.agent-mode-run .stButton>button{min-height:48px}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _route_agent(question: str, ctx: dict, mode: str) -> str:
    routed = route_mode_query(question, ctx)
    if routed:
        return routed
    if not question.strip():
        return agent_mode_reply(mode, ctx)
    return base.agent_reply(question, ctx)


def _select_mode() -> str:
    labels = list(AGENT_MODES.keys())
    if hasattr(st, "segmented_control"):
        selected = st.segmented_control(
            "Режим агента",
            labels,
            selection_mode="single",
            default=st.session_state.get("agent_mode", "Study"),
            key="agent_mode_segmented",
            format_func=lambda key: AGENT_MODES[key]["title"],
        )
        mode = selected or st.session_state.get("agent_mode", "Study")
        st.session_state["agent_mode"] = mode
        return str(mode)
    return st.radio(
        "Режим агента",
        labels,
        horizontal=True,
        key="agent_mode",
        format_func=lambda key: AGENT_MODES[key]["title"],
    )


def _render_compact_intro(mode: str) -> None:
    selected = AGENT_MODES[mode]
    st.markdown(
        "<div class='agent-mode-legend'>"
        + "".join([f"<span>{name}</span>" for name in AGENT_MODES])
        + "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='agent-mode-compact'><b>Компактный режим:</b> {selected['title']}"
        f"<p>{selected['goal']}</p>"
        f"<div class='agent-mode-details'><b>Выход:</b> {selected['output']}<br/><b>Граница:</b> {selected['guard']}</div></div>",
        unsafe_allow_html=True,
    )


def render_agent_panel(status: pd.DataFrame, swaps: pd.DataFrame, trades: pd.DataFrame, daily: pd.DataFrame, fee: pd.DataFrame, triggers: pd.DataFrame) -> None:
    ctx = base.build_agent_context(status, swaps, trades, daily, fee, triggers)
    _mode_css()

    st.markdown("### Агентурный слой Искры")
    st.markdown(
        "<span class='agent-badge'>Study</span><span class='agent-badge'>Analyze</span><span class='agent-badge'>Learn</span><span class='agent-badge'>Predict</span><span class='agent-badge'>Notify</span><span class='agent-badge'>Gather</span><span class='agent-badge'>Risk Guard</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='panel'><div class='small'>ГРАНИЦА АГЕНТА</div><p class='muted'>Агент изучает, анализирует, учится на прогонах, прогнозирует вероятность поддержки гипотезы, уведомляет о рисках, собирает информацию и предлагает research-step. Он не выдаёт финансовые рекомендации, не отдаёт BUY/SELL и всегда показывает риск и цену ошибки.</p></div>",
        unsafe_allow_html=True,
    )

    mode = _select_mode()
    _render_compact_intro(mode)
    render_active_mode_card(mode)

    st.markdown("<div class='agent-help'>Запуск выбранного режима:</div>", unsafe_allow_html=True)
    st.markdown("<div class='agent-mode-run'>", unsafe_allow_html=True)
    if st.button(f"Запустить {mode}", key="agent_run_selected_mode"):
        st.session_state.setdefault("agent_messages", [])
        st.session_state.agent_messages.append({"role": "assistant", "content": agent_mode_reply(mode, ctx)})
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("Runtime QA Panel", key="agent_runtime_qa_panel"):
        render_runtime_qa_panel(lambda prompt, qa_mode: _route_agent(prompt, ctx, qa_mode))

    if "agent_messages" not in st.session_state:
        st.session_state.agent_messages = [
            {"role": "assistant", "content": "Я агент membot. Выбери режим Study/Analyze/Learn/Predict/Notify/Gather или спроси: `что дальше?`, `оцени вероятность`, `какая цена ошибки?`, `что собрать?`."}
        ]
    for msg in st.session_state.agent_messages[-8:]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("Спроси агента о данных, режиме, риске, вероятности или следующем шаге", key="iskra_agent_chat")
    if prompt:
        st.session_state.agent_messages.append({"role": "user", "content": prompt})
        st.session_state.agent_messages.append({"role": "assistant", "content": _route_agent(prompt, ctx, mode)})
        st.rerun()

    with st.expander("Как устроен агентурный слой", key="agent_architecture"):
        tool_lines = "\n".join([f"- `{name}` — {desc}" for name, (desc, _) in base.AGENT_TOOLS.items()])
        st.markdown(
            f"""
            **Режимы:**\n{mode_lines_markdown()}

            **Инструменты v2** read-only:\n{tool_lines}

            **Guard** запрещает BUY/SELL и понижает вывод до UNKNOWN/PARTIAL при нехватке raw.  
            **Память v1** только session-state; долгую память подключаем позже через AgentMemory/MCP, без секретов.  
            **Уведомления** только про состояние и риск, не про торговое действие.
            """
        )

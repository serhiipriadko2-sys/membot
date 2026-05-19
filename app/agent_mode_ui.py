from __future__ import annotations

import pandas as pd
import streamlit as st

import agentic_layer as base
from agent_modes import AGENT_MODES, agent_mode_reply, mode_lines_markdown, render_active_mode_card, render_mode_cards, route_mode_query


def _mode_css() -> None:
    st.markdown(
        """
        <style>
        .agent-mode-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin:12px 0}
        .agent-mode-card{border:1px solid rgba(255,195,107,.17);border-radius:18px;padding:14px 16px;background:linear-gradient(180deg,rgba(13,18,30,.78),rgba(5,8,14,.70));min-height:260px;box-shadow:0 18px 46px rgba(0,0,0,.22),inset 0 1px 0 rgba(255,255,255,.04)}
        .agent-mode-card b{display:block;color:#FFF4D9;font-size:1.02rem;line-height:1.25;margin-bottom:.55rem;word-break:normal;overflow-wrap:normal;hyphens:none}.agent-mode-card p{color:#B7C3D1;line-height:1.55;margin:.35rem 0}.agent-mode-card small{display:block;color:#FFC36B;margin-top:.7rem;line-height:1.45}.agent-quick-grid{display:grid;grid-template-columns:repeat(6,minmax(86px,1fr));gap:10px;margin:18px 0 10px}.agent-quick-grid .stButton>button{width:100%;min-height:44px;white-space:nowrap;padding:.45rem .55rem}.agent-help{color:#9CA8B7;font-size:.9rem;margin:.4rem 0 1rem}
        @media(max-width:900px){.agent-mode-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.agent-mode-card{min-height:230px}.agent-quick-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}
        @media(max-width:560px){.agent-mode-grid{grid-template-columns:1fr}.agent-mode-card{min-height:auto}.agent-quick-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
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

    render_mode_cards()
    mode = st.radio(
        "Режим агента",
        list(AGENT_MODES.keys()),
        horizontal=True,
        key="agent_mode",
        format_func=lambda key: AGENT_MODES[key]["title"],
    )
    render_active_mode_card(mode)

    st.markdown("<div class='agent-help'>Быстрый запуск режима:</div>", unsafe_allow_html=True)
    quick_cols = st.columns(6)
    for idx, quick_mode in enumerate(AGENT_MODES):
        if quick_cols[idx].button(quick_mode, key=f"agent_quick_{quick_mode}"):
            st.session_state.setdefault("agent_messages", [])
            st.session_state.agent_messages.append({"role": "assistant", "content": agent_mode_reply(quick_mode, ctx)})
            st.rerun()

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

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import agent_modes  # noqa: E402
from agent_runtime_qa import run_agent_qa  # noqa: E402


CTX = {
    "artifacts_found": 0,
    "artifact_rows": 0,
    "swaps_rows": 0,
    "trades_rows": 0,
    "daily_rows": 0,
    "fee_rows": 0,
    "trigger_rows": 0,
    "missing_critical": [
        "wallet_swaps",
        "trades_paired",
        "daily_pnl_calendar",
        "priority_fee_jito_audit",
    ],
    "critical_coverage_pct": 0,
}


def _patch_streamlit_state() -> None:
    # agent_modes.tool_learn_mode uses st.session_state. In CI we do not run
    # through `streamlit run`, so provide a tiny compatible object.
    agent_modes.st = SimpleNamespace(session_state={})


def response_fn(prompt: str, mode: str) -> str:
    _patch_streamlit_state()
    routed = agent_modes.route_mode_query(prompt, CTX)
    if routed:
        return routed
    return agent_modes.agent_mode_reply(mode, CTX)


def main() -> int:
    df = run_agent_qa(response_fn)
    print(df.to_string(index=False))
    failures = df[df["verdict"] == "FAIL"]
    if not failures.empty:
        print("AGENT_CI_SMOKE_FAIL: forbidden directive or runtime error detected.")
        return 1
    warnings = df[df["verdict"] == "WARN"]
    if not warnings.empty:
        print("AGENT_CI_SMOKE_WARN: missing expected markers; review output quality.")
        return 1
    print("AGENT_CI_SMOKE_PASS: all agent QA cases passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

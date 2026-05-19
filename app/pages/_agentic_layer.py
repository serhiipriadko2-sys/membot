from __future__ import annotations

# Compatibility shim for Streamlit Cloud.
#
# 00_Iskra_Forge.py imports `_agentic_layer`. Depending on how Streamlit runs
# st.Page files, Python can resolve this page-local helper before the root-level
# app/_agentic_layer.py shim. Keep this file thin and forward everything to the
# canonical root modules so old Onboarding/Data QA UI cannot shadow the v3
# Study/Analyze/Learn/Predict/Notify/Gather agent panel.

from agentic_layer import *  # noqa: F401,F403
from agent_mode_ui import render_agent_panel  # noqa: F401

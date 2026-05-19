# Streamlit hotfix: duplicate elements and page icons

## Problem
The deployed app showed two separate Streamlit errors:

1. `StreamlitDuplicateElementId`
   - Triggered when identical Plotly charts were rendered in multiple tabs without explicit keys.
   - The same chart can appear in the Signal Forge overview and dataset tabs.

2. `StreamlitAPIException` in `st.Page(...)`
   - Caused by invalid `icon` values such as `"*"` and `"DB"`.
   - Streamlit validates page icons strictly.

## Fix

### Navigation
`app/streamlit_app.py` now omits page icons:

```python
pages = [
    st.Page("pages/00_Iskra_Forge.py", title="Iskra Forge", default=True),
    st.Page("pages/01_Supabase_Bridge.py", title="Data Bridge"),
]
```

### Plotly charts
`app/pages/00_Iskra_Forge.py` now requires a unique `key` for `render_plot(...)`, and passes those keys through to `st.plotly_chart(...)`.

Examples:

```python
render_plot(..., key="forge_cluster_map")
render_plot(..., key="dataset_wallet_swaps_cluster")
render_plot(..., key="dataset_priority_fee_jito_audit_fee")
```

## QA
PASS if:
- Sidebar loads with no `st.Page` icon error.
- Opening Raw/FIFO/Daily PnL/Fee/Jito/Triggers does not throw `StreamlitDuplicateElementId`.
- Charts can appear in both overview and detail tabs without collision.

## Guardrail
This is a runtime stability hotfix only. It does not change forensic verdicts.

# Single Forge navigation

## Problem
Streamlit automatically listed every file in `app/pages/`, producing a noisy sidebar:
- Iskra Forge
- Signal Forge
- Supabase Bridge
- Entry Exit Hypotheses
- Daily PnL and Fees

That made the product feel like a page graveyard instead of a single premium forensic interface.

## Decision
Use explicit Streamlit navigation from `app/streamlit_app.py`:
- `Iskra Forge` — main product interface
- `Data Bridge` — Supabase/load/save bridge

Remove old active pages from `app/pages`:
- `00_Signal_Forge.py`
- `08_Entry_Exit_Hypotheses.py`
- `09_Daily_PnL_and_Fees.py`

The old functionality is already represented inside Iskra Forge widgets/tables/reports.

## Product rule
One mental model:

`Forge -> Data Bridge -> Tables -> Reports`

No duplicate top-level screens.

## QA
PASS if the sidebar no longer shows legacy duplicate pages.

Expected sidebar:
- Iskra Forge
- Data Bridge

If Streamlit Cloud version does not support `st.navigation`, fallback is to keep only one file in `app/pages` and move Data Bridge into a section inside `00_Iskra_Forge.py`.

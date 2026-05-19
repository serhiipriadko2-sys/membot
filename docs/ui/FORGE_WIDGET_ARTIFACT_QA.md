# Forge widget artifact QA

## Goal
Verify that a forensic workflow artifact can power the four live Iskra Forge widgets before relying on the Streamlit view.

## Required artifact members
- `data/processed/wallet_swaps.csv` for cluster map
- `data/processed/daily_pnl_calendar.csv` for Daily PnL calendar
- `data/processed/priority_fee_jito_audit.csv` for Fee/Jito orbit
- `data/processed/trigger_tests.csv` for trigger radar and signal cards

Fallbacks:
- cluster map can use `data/processed/trades_paired.csv`
- trigger cards can use `data/processed/entry_exit_hypothesis_tests.csv`

## Command
```bash
python scripts/verify_forge_artifact_widgets.py forensic-verification-<run_id>.zip --json forge_widget_qa.json
```

Expected final verdict:
- `PASS`: all four widgets have usable source files and required columns
- `PARTIAL`: at least one widget can render, others need mapping/artifacts
- `UNKNOWN`: no widget has sufficient data

## Streamlit check
After PASS/PARTIAL:
1. Open the deployed app.
2. Go to Upload.
3. Upload the CSV files from the artifact.
4. Return to Signal Forge.
5. Confirm:
   - cluster map renders from wallet swaps or paired trades
   - Daily PnL heatmap renders from daily calendar
   - Fee/Jito donut renders from audit rows
   - trigger radar and signal cards render from trigger/hypothesis rows

## Guardrail
A chart rendering is not a trading signal. It only proves UI readiness. Raw forensic verdicts still require FIFO, fee/Jito audit, controls, and out-of-sample checks.

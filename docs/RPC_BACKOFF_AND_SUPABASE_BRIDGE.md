# RPC backoff and Supabase Bridge fix

## Context
The first `limit=600` forensic artifact fetched 600 signatures but only 2 transaction payloads. Most transaction fetches failed with public Solana RPC `429 Too Many Requests`.

The Iskra Forge UI also lost Supabase source selection after the old `streamlit_app.py` was replaced by the new visual entrypoint.

## Changes

### RPC/fetch layer
- `scripts/common.py`
  - adds bounded retry/backoff for RPC transport errors and selected transient RPC errors
  - reads retry controls from env:
    - `RPC_MAX_RETRIES`
    - `RPC_BACKOFF_BASE_SECONDS`
    - `RPC_BACKOFF_MAX_SECONDS`
    - `RPC_TIMEOUT_SECONDS`
    - `RPC_JITTER_SECONDS`
- `scripts/02_fetch_transactions.py`
  - resumable by default
  - skips already fetched transaction rows
  - records coverage percentage
  - supports `--no-resume` and `--max-errors`
- `.github/workflows/run_forensic_verification.yml`
  - timeout raised to 90 minutes
  - slower request cadence and stronger retry env defaults

### Supabase Bridge
- `app/pages/01_Supabase_Bridge.py`
  - restores Supabase run listing
  - loads `dataset_artifacts` into `st.session_state["sf_uploaded"]`
  - allows uploaded CSV/MD/JSON/TXT artifacts to be saved back to Supabase
  - keeps Iskra Forge as the main visual UI

### Iskra Forge mapping
- `app/pages/00_Iskra_Forge.py`
  - supports `hypothesis_id` as signal name
  - supports `support_rate_pct` as signal score
  - keeps PASS/PARTIAL as evidence support, not a buy command

## Required secrets
- `SOLANA_RPC_URL` in GitHub Actions for stable fetches
- `SUPABASE_URL` in Streamlit secrets
- `SUPABASE_SERVICE_ROLE_KEY` or `SUPABASE_KEY` in Streamlit secrets
- optional `APP_ACCESS_PIN` for UI gate

## Verification flow
1. Merge this PR.
2. Set/verify `SOLANA_RPC_URL` in GitHub secrets.
3. Run `Run forensic verification` with `limit=600`.
4. Download artifact.
5. Run:
   ```bash
   python scripts/verify_forge_artifact_widgets.py forensic-verification-<run_id>.zip --json forge_widget_qa.json
   ```
6. Open Streamlit:
   - use `Supabase Bridge` to load/save runs
   - return to `Iskra Forge` to render live widgets

## Guardrail
This improves data availability and UI flow. It does not prove the trading edge. Forensic verdict still requires raw transaction coverage, FIFO, fee/Jito audit, controls, and out-of-sample checks.

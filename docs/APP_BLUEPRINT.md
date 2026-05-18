# membot forensic app blueprint

## Status

```text
APP_LAYER: READ-ONLY MVP
TRADING: FORBIDDEN
PRIVATE_KEYS: FORBIDDEN
FINAL_ALGORITHM_CLAIM: FORBIDDEN
```

This application layer is a local dashboard around generated forensic artifacts. It must not execute trades, create orders, hold private keys, or present dashboard output as final proof of the wallet algorithm.

## Why Streamlit first

Streamlit is suitable for this repository because the current workflow is CSV/report driven and research-oriented. The app can read local `data/processed/*.csv` and `reports/*.md` without changing the existing Python pipeline.

FastAPI may be added later only when we need an API service, background jobs, authentication, or multi-user deployment.

## Entry point

```bash
streamlit run app/streamlit_app.py
```

## Inputs

The app reads these optional artifacts:

```text
data/processed/wallet_swaps.csv
data/processed/trades_paired.csv
data/processed/latency_sim.csv
data/processed/fee_adjusted_pnl.csv
data/processed/copy_stress_model.csv
data/processed/entry_context.csv
data/processed/trigger_tests.csv
data/processed/open_positions.csv
reports/*.md
```

Missing files are expected during early research. The app must show missing-file messages, not fail.

## Tabs

```text
Overview
Swaps
Paired trades
Latency / copy
Entry context
Reports
```

## Guardrails

- Read-only local files only.
- No private key fields.
- No trading execution.
- No GMGN swap/cooking/order creation.
- No final claims from dashboard metrics.
- Copy-stress output is not latency replay.
- `entry_context` requires control-point comparison before predictor claims.

## Future app layers

### v0.2

```text
- Upload CSV through UI
- Run fixture-only parser checks
- Export HTML/PDF report
- Add security scan panel
```

### v0.3

```text
- Controlled pipeline runner for local scripts
- Helius/Dune import status panel
- Manual audit workflow for random signatures
```

### v1.0

```text
- FastAPI backend
- job queue
- persistent database
- user auth
- hosted read-only deployment
```

## Development commands

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m py_compile app/streamlit_app.py
streamlit run app/streamlit_app.py
```

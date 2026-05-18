# Scripts

This directory contains the membot forensic dataset pipeline — fetch,
parse, pair, and analyse Solana wallet activity.

## Pipeline Execution Order

```
00_check_rpc_health.py      # Health gate — probe all configured RPC endpoints
01_fetch_signatures.py      # Fetch wallet signatures from Solana RPC
02_fetch_transactions.py    # Fetch full transactions for those signatures
03_normalize_swaps.py       # Extract swap rows → data/processed/wallet_swaps.csv
04_pair_trades.py           # Pair buys/sells → data/processed/trades_paired.csv
```

**Always run step 00 first.** If it exits non-zero, fix your RPC config
before proceeding. See `docs/RPC_PROVIDER_STRATEGY.md`.

## Later stages (analysis)

```
06_build_price_series.py
07_latency_sim.py
09_metrics_report.py
10_parse_gmgn_trend_snapshot.py
11_import_trade_export.py
12_fee_adjusted_pnl.py
13_copy_stress_model.py
14_backtest_report.py
16_reconcile_open_positions_fifo.py
18_build_entry_context.py   # Build leakage-safe 30 winner / 30 loser pre-entry sample
19_build_control_points.py  # Build same-token control points for trigger testing
20_test_entry_triggers.py   # Test entry-vs-control feature separation
```

## Pre-entry context study

`18_build_entry_context.py` creates `data/processed/entry_context.csv` from
existing local artifacts. It does not perform RPC calls and does not fabricate
market-wide metrics. Missing external market context is marked `UNKNOWN`.

Default run:

```bash
python scripts/18_build_entry_context.py --sample-winners 30 --sample-losers 30
```

`19_build_control_points.py` creates `data/processed/control_points.csv` from
entry context rows and matched same-token offsets. Default controls are pre-entry
only: `-300s`, `-120s`, `-60s`.

Default run:

```bash
python scripts/19_build_control_points.py
```

`20_test_entry_triggers.py` compares `entry_context.csv` against
`control_points.csv` using `configs/prebuy_feature_manifest.yaml` and writes:

```text
data/processed/trigger_tests.csv
reports/prebuy_trigger_report.md
```

Default run:

```bash
python scripts/20_test_entry_triggers.py
```

See `docs/ENTRY_CONTEXT_PROTOCOL.md` for leakage rules, feature metadata, and
control-point limitations.

## Principles

- Script outputs write reproducible artifacts, not only console summaries.
- No fake data: if an upstream step failed, downstream steps refuse to run.
- All RPC settings come from `.env` (see `.env.example`).

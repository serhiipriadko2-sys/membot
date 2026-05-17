# Scripts

This directory contains the membot forensic dataset pipeline — fetch,
parse, pair, and analyse Solana wallet activity.

## Pipeline Execution Order

```
00_check_rpc_health.py      # Health gate — probe all configured RPC endpoints
01_fetch_signatures.py      # Fetch wallet signatures from Solana RPC
02_fetch_transactions.py    # Fetch full transactions for those signatures
03_normalize_swaps.py       # Extract swap rows → data/parsed/wallet_swaps.csv
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
```

## Principles

- Script outputs write reproducible artifacts, not only console summaries.
- No fake data: if an upstream step failed, downstream steps refuse to run.
- All RPC settings come from `.env` (see `.env.example`).


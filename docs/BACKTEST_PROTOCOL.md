# Backtest protocol

Status: `READY FOR BACKTEST PIPELINE DESIGN`.

Not status:

```text
READY FOR INDEPENDENT PNL CLAIM
READY FOR COPY-TRADE DECISION
ALGORITHM DECODED
SAFE TO COPY
```

## Truth order

1. Raw trade exports from Dune / Helius / manual CSV.
2. Normalized `wallet_swaps.csv`.
3. FIFO / audited pairing.
4. Observed fee-adjusted PnL.
5. Copy-stress economics.
6. Latency replay only when `price_series.csv` exists.

## Required outputs

```text
data/processed/wallet_swaps.csv
data/processed/fee_adjusted_pnl.csv
data/processed/copy_stress_model.csv
reports/backtest_report.md
```

## Guardrails

- No auto-trading.
- No GMGN private key.
- No `gmgn-cli swap`.
- No `gmgn-cli cooking`.
- No order creation.
- No final claim: `algorithm decoded`.
- No final claim: `safe to copy`.
- Stress model is not latency replay unless real delayed price data exists.

## Copy-stress versus latency replay

`copy_stress_model.csv` is a formulaic stress test. It worsens entry/exit economics using configured slippage and fees.

It is not a true delayed-entry replay.

`latency_replay` stays `UNKNOWN` unless `price_series.csv` exists and contains delayed-entry prices.

## Fee policy

Observed wallet PnL uses only observed fees from exports. Missing observed fee must remain missing/low-confidence and must not be replaced by GMGN copy fees.

Copy-stress model separately applies simulated copy costs:

```text
gmgn_fee_pct = 1% on buy notional + sell notional
extra_fee_usd_per_trade = configurable, default 0.05
```

## Report requirements

Every `reports/backtest_report.md` must state:

```text
This report is not a trading recommendation.
This report does not prove the wallet algorithm.
Copy-stress model is not latency replay.
Latency replay is UNKNOWN unless price_series.csv exists.
```

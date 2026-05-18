# M3.2 — market-wide pre-entry context

## Status

```text
M3.2_STATUS: PATCHED
TRADING_SIGNAL: NOT CLAIMED
DATA_QUALITY_PASS: SEPARATE_FROM_TRADING_TRIGGER
MARKET_CONTEXT: REQUIRED
```

## Why this patch exists

The M3 dense wallet-derived run produced a useful but dangerous pattern: `feature_coverage_pct` could pass while actual market/trading features remained weak or unknown.

M3.2 separates:

```text
data_quality verdicts
trading_trigger verdicts
```

A data-quality pass must never be displayed or interpreted as a buy/sell signal.

## Patched trigger testing

`scripts/20_test_entry_triggers.py` now adds:

```text
feature_role
nonzero_rate_entry
nonzero_rate_control
variance_entry
variance_control
unique_values_count
information_status
status_reason
```

Guardrails:

```text
constant feature -> NO_SIGNAL
zero variance -> NO_SIGNAL
low coverage -> UNKNOWN
data_quality strong separation -> DATA_QUALITY_PASS, not PASS
precision_at_k is tie-aware
auc is 0.5 for constant features
```

## New market artifact

```text
data/processed/market_same_token_swaps.csv
```

This artifact is intended to hold market-wide same-token swap rows around the tokens and windows being studied.

It is created with:

```bash
python scripts/21_build_market_same_token_swaps.py \
  --input data/external/dune_market_same_token_swaps.csv \
  --entry-context data/processed/entry_context.csv \
  --output data/processed/market_same_token_swaps.csv
```

## Dune export path

1. Open Dune.
2. Create a query from:

```text
sql/dune_market_same_token_swaps.sql
```

3. Replace `target_mints` with token mints from `entry_context.csv`.
4. Set the time window around the sample.
5. Export CSV.
6. Save as:

```text
data/external/dune_market_same_token_swaps.csv
```

7. Run `scripts/21_build_market_same_token_swaps.py`.

## Important limitations

`dex_solana.trades` may contain multiple rows for multi-hop swaps. The normalized market artifact is valid for market-flow context, but it is not final accounting PnL unless tx-level grouping/audit is added.

## Next step

Use `market_same_token_swaps.csv` to enrich `entry_context.csv` with market-wide features:

```text
market_buy_count_30s
market_sell_count_30s
market_volume_usd_30s
market_unique_buyers_30s
market_net_buy_usd_30s
market_price_return_30s
market_tx_rate_30s
```

These features should be compared against matched controls and OOS before any predictor claim.

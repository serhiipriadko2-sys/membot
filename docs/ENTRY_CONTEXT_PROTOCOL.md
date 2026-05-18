# Entry Context Protocol

## Goal

Move the wallet study from post-trade description to pre-entry evidence.
`wallet_swaps.csv` and `trades_paired.csv` show what happened after a BUY.
`entry_context.csv` is the first leakage-safe dataset for asking what was
observable before the BUY.

## Truth order

1. Raw transaction exports.
2. Reproducible parsers and pairing logic.
3. Generated entry-context and control-point reports.
4. Manual audit of ambiguous rows.
5. Dashboard summaries only as hints.

## Leakage guard

Every feature in `entry_context.csv` must be computed from data strictly before
`entry_signature`.

Rules:
- Exclude the entry transaction itself.
- Exclude every row after the entry block time.
- For equal block time, accept only lower slot as before.
- Same-slot ordering is not trusted without a dedicated slot/order enrichment.
- Missing market-wide fields must remain `UNKNOWN`; do not fabricate values.

## Current M2 scope

`scripts/18_build_entry_context.py` creates a balanced sample from existing
local artifacts only:

```text
data/processed/wallet_swaps.csv
data/processed/trades_paired.csv
data/processed/price_series.csv
```

Default output:

```text
data/processed/entry_context.csv
```

Default sample:

```text
30 winners + 30 losers
```

## Feature metadata

Every entry-context row includes machine-readable metadata:

- `feature_family` — semicolon-separated families observed from available data.
  Current wallet-derived families: `wallet_flow`, `price_action`, `repeat_wave`,
  or `none`.
- `feature_source` — concrete local sources used for known features, such as
  `wallet_swaps` or `wallet_swaps;price_series`.
- `feature_coverage_pct` — percent of expected feature fields populated with
  non-UNKNOWN values.
- `confidence` — `medium` for wallet price + swap coverage, `low` for swap-only,
  `unknown` when no pre-entry coverage exists.

## Control points

`scripts/19_build_control_points.py` creates matched controls from local data:

```text
data/processed/entry_context.csv
data/processed/wallet_swaps.csv
data/processed/price_series.csv
```

Default output:

```text
data/processed/control_points.csv
```

Default controls are same-token pre-entry offsets:

```text
-300s, -120s, -60s before entry
```

Post-entry controls are excluded unless `--include-after` is explicitly passed.
Rows with post-entry controls are marked `leakage_guard_ok=false` and must not be
used for leakage-safe predictor claims.

## Coverage semantics

- `market_coverage=wallet_only` means no Dune/Helius/getBlock market-wide
  context was used.
- `context_status=UNKNOWN` means the script found no usable pre-entry wallet or
  price context for that row.
- `context_status=PARTIAL` means some wallet-derived pre-entry context exists,
  but it is not yet enough to prove market triggers.

## Non-claims

This layer does not prove prediction by itself. It prepares rows for later
comparison against control points.

Do not claim H4 PASS until entries are compared against matched controls in
`control_points.csv` / `trigger_tests.csv`.

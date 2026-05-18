# Research Backlog 2026

## Priority 0 — Evidence hygiene

- Keep all infrastructure claims in `docs/SOURCE_AUDIT_2026.md`.
- Do not promote PENDING source claims into code comments as facts.
- Keep all unimplemented features marked with `implemented: false` and `status: HYPOTHESIS`.
- Do not claim trigger discovery without generated validation outputs.
- Treat any exposed RPC key prefix as compromised and rotate it.

## Current dataset audit status

See `docs/RUN_AUDIT_2026_05_17.md`.

Known user-provided run status:

```text
limit 100:   100 swaps, 24 paired trades, 0 fetch errors
limit 1000:  981 swaps, 438 paired trades, 5 read timeouts, 0.5% fetch error rate
```

This is enough to continue dataset-building and entry-vs-control validation.
It is not evidence that a trigger has been found.

## Priority 1 — Runtime data restoration

Needed to run validation:

```text
data/processed/wallet_swaps.csv
data/processed/trades_paired.csv
data/processed/price_series.csv
data/processed/entry_context.csv
data/processed/control_points.csv
```

Optional:

```text
data/processed/cross_chain_events.csv
data/processed/cluster_context.csv
data/processed/cross_chain_context.csv
```

If only `wallet_swaps.csv` and `trades_paired.csv` exist, regenerate:

```bash
python scripts/06_build_price_series.py
python scripts/18_build_entry_context.py --sample-winners 30 --sample-losers 30
python scripts/19_build_control_points.py
```

## Priority 2 — Run existing validation harness

```bash
python scripts/06_build_price_series.py
python scripts/18_build_entry_context.py --sample-winners 30 --sample-losers 30
python scripts/19_build_control_points.py
python scripts/20_test_entry_triggers.py
python scripts/21_build_cluster_context.py
python scripts/22_build_cross_chain_context.py
python scripts/23_test_cluster_triggers.py
python scripts/24_test_cross_chain_triggers.py
```

Outputs:

```text
data/processed/trigger_tests.csv
reports/prebuy_trigger_report.md
data/processed/cluster_trigger_tests.csv
reports/cluster_trigger_report.md
data/processed/cross_chain_trigger_tests.csv
reports/cross_chain_trigger_report.md
```

## Priority 3 — Source-audit backlog

- Verify Helius Enhanced/LaserStream status from official Helius docs.
- Verify PumpSwap migration claims from official pump.fun / PumpSwap docs or trusted primary data.
- Verify Token-2022 extension risk flags from official Solana SPL docs.
- Verify RugCheck insider-network claims from primary RugCheck docs.
- Audit academic claims for VPIN, HMM, entropy filtering, and cross-chain sybil detection.

## Priority 4 — Feature implementation backlog

### H11: VPIN / toxicity

- Build market trade buckets.
- Implement VPIN / OFI features.
- Add `vpin_trigger_tests.csv`.

### H12: Graduation crescendo

- Build bonding curve state snapshots.
- Add curve velocity and acceleration.
- Match controls by token age and liquidity bucket.

### H13: Regime-aware momentum

- Add regime labels.
- Compare fixed thresholds vs regime-conditioned thresholds.
- Use out-of-sample split.

### H14: Reflexivity feedback

- Build attention timeline.
- Add price-volume-attention loop proxies.
- Validate against controls.

## Priority 5 — Production blockers

No production decision logic until:

- source audit completed for any external data source used;
- runtime CSV generated and committed only as artifacts outside repo if needed;
- OOS validation exists;
- latency / fee / slippage replay exists;
- secret scan is clean;
- all non-claims remain documented.

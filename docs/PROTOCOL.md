# Research Protocol

## Aim

Build a reproducible dataset and evaluation loop for the target wallet before making any claim about strategy or edge.

## Truth order

1. Raw on-chain transaction exports.
2. Reproducible parsing and pairing logic in code.
3. Generated reports from the exact dataset.
4. Entry-vs-control validation outputs.
5. Manual audit notes for ambiguous rows.
6. External dashboards only as hints, never as final proof.

## Core workflow

1. Fetch signatures for the wallet over a defined time window.
2. Fetch full transactions with slot, blockTime, balances and metadata.
3. Normalize swaps from raw balance deltas and instruction context.
4. Pair buys and sells under explicit rules.
5. Build pre-entry context.
6. Build matched control points.
7. Run trigger separation tests.
8. Add cluster / cross-chain / execution context only as separately validated layers.
9. Generate fee, slippage, latency, and inventory reports.
10. Audit low-confidence rows before interpreting the results.

## Working hypotheses

- H1: the wallet is a short-horizon scalper.
- H2: the edge is concentrated in ultra-small-cap setups.
- H3: execution quality materially affects realized PnL.
- H4: entries cluster around observable event triggers.

2026 expansion:
- H11: VPIN / toxicity surge may precede sharp moves.
- H12: bonding-curve or graduation crescendo may precede migration/attention.
- H13: regime-aware momentum may outperform fixed thresholds.
- H14: reflexivity / feedback inflection may explain attention-driven memecoin moves.

All 2026 expansion items are HYPOTHESIS until tested.

## Evidence discipline

Every future report should mark statements as one of:

- FACT
- INTERPRETATION
- HYPOTHESIS
- UNKNOWN
- FALSE

A metric is not a fact until the dataset, code path and output file can be reproduced.

## Source audit discipline

A claim sourced from a paper, API document, dashboard, or research report must be tracked in `docs/SOURCE_AUDIT_2026.md` before becoming project evidence.

Source statuses:

- VERIFIED: official source or primary paper checked.
- PARTIAL: source exists but interpretation or freshness still uncertain.
- PENDING: claim exists in research notes but source has not been checked.
- REJECTED: source does not support the claim.

## Dataset minimum

A usable dataset must eventually include:

- signatures
- raw transactions
- normalized wallet swaps
- paired trades
- entry context
- matched controls
- trigger tests
- cluster context when used
- cross-chain context when used
- fee and tip scan output
- latency simulation output
- metrics report

## Trigger claim acceptance

A trigger family can be upgraded only through validation:

- UNKNOWN: missing data or coverage below threshold.
- NO_SIGNAL: data exists but separation is weak.
- PARTIAL: directional entry-vs-control separation exists but still needs broader coverage or OOS.
- PASS: entry-vs-control and winner-vs-loser evidence is strong, with OOS and latency/slippage checks.
- FAIL: controls contradict the trigger or signal disappears after realistic costs/delay.

## Known hard parts

- Multi-hop routes may break naive swap parsing.
- WSOL wrapping can distort SOL deltas.
- Block-order analysis requires slot-level context.
- Jito usage cannot be proven from tips alone.
- Event-trigger testing requires control points, not only entry points.
- Cluster presence can be bullish, toxic, or a single-controller sybil pattern.
- Cross-chain context is regime context, not direct token-level proof.
- Social/attention signals are easy to overfit.

## Repository rule

This repository should prefer explicit unknowns over confident fiction.

# Research Protocol

## Aim

Build a reproducible dataset and evaluation loop for the target wallet before making any claim about strategy or edge.

## Truth order

1. Raw on-chain transaction exports.
2. Reproducible parsing and pairing logic in code.
3. Generated reports from the exact dataset.
4. Manual audit notes for ambiguous rows.
5. External dashboards only as hints, never as final proof.

## Core workflow

1. Fetch signatures for the wallet over a defined time window.
2. Fetch full transactions with slot, blockTime, balances and metadata.
3. Normalize swaps from raw balance deltas and instruction context.
4. Pair buys and sells under explicit rules.
5. Generate metrics and latency-sensitivity outputs.
6. Audit low-confidence rows before interpreting the results.

## Working hypotheses

- H1: the wallet is a short-horizon scalper.
- H2: the edge is concentrated in ultra-small-cap setups.
- H3: execution quality materially affects realized PnL.
- H4: entries cluster around observable event triggers.

## Evidence discipline

Every future report should mark statements as one of:
- FACT
- INTERPRETATION
- HYPOTHESIS

A metric is not a fact until the dataset, code path and output file can be reproduced.

## Dataset minimum

A usable dataset must eventually include:
- signatures
- raw transactions
- normalized wallet swaps
- paired trades
- fee and tip scan output
- latency simulation output
- metrics report

## Known hard parts

- Multi-hop routes may break naive swap parsing.
- WSOL wrapping can distort SOL deltas.
- Block-order analysis requires slot-level context.
- Jito usage cannot be proven from tips alone.
- Event-trigger testing requires control points, not only entry points.

## Repository rule

This repository should prefer explicit unknowns over confident fiction.

# Pre-buy Trigger Test Report

## Summary

- Entry rows: `1000`
- Control rows: `3000`
- Trigger tests: `12`
- Guardrail: `DATA_QUALITY_*` verdicts are not trading triggers.
- Guardrail: constant / zero-variance features cannot become PASS.
- Guardrail: this report does not prove H4 without sufficient coverage, controls, and out-of-sample validation.

## Verdict counts

- `NO_SIGNAL`: `6`
- `PARTIAL`: `2`
- `PASS`: `3`
- `UNKNOWN`: `1`

## Feature role counts

- `research_signal`: `12`

## Information status counts

- `LOW_COVERAGE`: `1`
- `VARIABLE`: `11`

## Dune aggregate guardrail

This report validates precomputed Dune anchor features only. It is not a trading signal, not raw wallet accounting, and not final proof of a trigger until the canonical raw/FIFO, fee, latency, slippage, and out-of-sample checks pass.

## Source row grouping

- source row ids: `1000`
- complete 1-entry / 3-control groups: `1000 / 1000`
- groups without exactly one entry: `0`
- groups without exactly three controls: `0`

# Pre-buy Trigger Test Report

## Summary

- Entry rows: `60`
- Control rows: `180`
- Trigger tests: `56`
- Guardrail: `DATA_QUALITY_*` verdicts are not trading triggers.
- Guardrail: constant / zero-variance features cannot become PASS.
- Guardrail: this report does not prove H4 without sufficient coverage, controls, and out-of-sample validation.

## Verdict counts

- `DATA_QUALITY_NO_SIGNAL`: `2`
- `NO_SIGNAL`: `12`
- `UNKNOWN`: `42`

## Feature role counts

- `data_quality`: `2`
- `trading_trigger`: `54`

## Information status counts

- `CONSTANT`: `6`
- `EMPTY`: `40`
- `LOW_COVERAGE`: `2`
- `VARIABLE`: `8`

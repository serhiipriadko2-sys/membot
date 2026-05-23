# Observer Live-Run Gate Report

- Source: `data\processed\observer_latency_live.csv`
- Status: `SMOKE_ONLY`
- Verdict: `SMOKE_ONLY`
- Run mode: `smoke`
- Safety: `monitoring only`, `NO_PRIVATE_KEYS`, `NO_SIGNING`, `NO_SWAP_SEND`

Observer harness validated; live network run pending.

## Metrics

| Metric | Value |
|---|---:|
| rows | `1` |
| quote_success_count | `1` |
| coverage_pct | `100.0` |
| p50_total_latency_ms | `345.0` |
| p90_total_latency_ms | `345.0` |
| p50_quote_latency_ms | `250.0` |
| p90_quote_latency_ms | `250.0` |
| p50_detector_latency_ms | `95.0` |
| p90_detector_latency_ms | `95.0` |

## Reasons

- run mode is not live
- row count 1 below live minimum 50

## Decision Boundary

Paper mode is blocked unless Gate 2 returns `PASS` on a real network-enabled run.
Live execution remains forbidden until a separate security review, private-key boundary, slippage replay, fail-safe, and explicit approval.

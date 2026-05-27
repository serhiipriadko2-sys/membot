# Observer Live-Run Gate Report

- Source: `/workspace/data/processed/observer_latency_live.csv`
- Status: `ACTIVE / GATE FAILED`
- Verdict: `FAIL`
- Run mode: `smoke`
- Safety: `monitoring only`, `NO_PRIVATE_KEYS`, `NO_SIGNING`, `NO_SWAP_SEND`

## Metrics

| Metric | Value |
|---|---:|
| rows | `0` |
| quote_success_count | `0` |
| coverage_pct | `0.0` |
| p50_total_latency_ms | `None` |
| p90_total_latency_ms | `None` |
| p50_quote_latency_ms | `None` |
| p90_quote_latency_ms | `None` |
| p50_detector_latency_ms | `None` |
| p90_detector_latency_ms | `None` |

## Reasons

- input not found: /workspace/data/processed/observer_latency_live.csv
- missing required latency fields
- no latency rows
- missing_fields: `signal_ts_ms, detected_ts_ms, quote_start_ts_ms, quote_end_ts_ms, detector_latency_ms, quote_latency_ms, total_latency_ms, quote_ok, error`

## Decision Boundary

Paper mode is blocked unless Gate 2 returns `PASS` on a real network-enabled run.
Live execution remains forbidden until a separate security review, private-key boundary, slippage replay, fail-safe, and explicit approval.

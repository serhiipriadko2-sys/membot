# Observer Status - 2026-05-23

## Verdict

```text
ready-for-live-run / current gate failed
```

Canonical wording:

```text
Observer harness validated; live network run pending.
```

## What is accepted

- No-key observer harness source is present.
- Smoke-only latency CSV emitter is present.
- Gate evaluator is present.
- Package audit script is present.
- Runbook is present.

## What is not accepted as proof

- A single smoke row is not a live network run.
- `595 ms` without raw rows and component breakdown is a technical warning, not a strategy verdict.
- Status text alone is not source of truth.
- Dashboard wording is below raw CSV and gate report.

## Required raw artifact

```text
observer_latency_live.csv
```

Required fields:

```text
signal_ts_ms
detected_ts_ms
quote_start_ts_ms
quote_end_ts_ms
detector_latency_ms
quote_latency_ms
total_latency_ms
quote_ok
error
```

## Gate 2 minimum

```text
row_count >= 50
coverage >= 90%
p50 total_latency_ms < 500
p90 total_latency_ms < 1000
p50/p90 quote_latency_ms populated
p50/p90 detector_latency_ms populated
NO_PRIVATE_KEYS
NO_SIGNING
NO_SWAP_SEND
```

## Decision boundary

Paper mode remains blocked until Gate 2 PASS.

Live execution remains forbidden until a separate security review, private-key
boundary, slippage replay, fail-safe, and explicit approval.

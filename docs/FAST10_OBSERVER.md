# Fast10 Observer

## Purpose

This is a no-key observer harness for the Fast10 execution lab.

It is **not** a trading bot and it is **not** a live-alpha proof.

Canonical current wording:

```text
Observer harness validated; live network run pending.
```

The observer exists to answer one question:

```text
Can a Fast10-compatible candidate be detected and quoted fast enough in a real
network-enabled monitoring run?
```

## Current implementation status

```text
ready-for-live-run / current gate failed until observer_latency_live.csv passes
```

Already in repo:

- `scripts/fast10_observer.py` - no-key Jupiter quote latency harness.
- `scripts/fast10_detector_emitter.py` - smoke-only CSV plumbing emitter.
- `scripts/observer_gate_eval.py` - latency gate evaluator.
- `scripts/observer_package_audit.py` - delivery ZIP integrity and secret audit.
- `README_RUNBOOK.md` - operational runbook.

What it does **not** do:

- sign transactions;
- place orders;
- move funds;
- prove live alpha;
- authorize Paper or Live execution.

## Mandatory latency artifact

The canonical observer artifact is:

```text
data/processed/observer_latency_live.csv
```

Required columns:

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

Meaning:

- `signal_ts_ms` - when the signal/candidate was observed in source time.
- `detected_ts_ms` - when local detector emitted the candidate.
- `quote_start_ts_ms` - when quote request started.
- `quote_end_ts_ms` - when quote response or failure was recorded.
- `detector_latency_ms` - `detected_ts_ms - signal_ts_ms`.
- `quote_latency_ms` - `quote_end_ts_ms - quote_start_ts_ms`.
- `total_latency_ms` - `quote_end_ts_ms - signal_ts_ms`.
- `quote_ok` - true only if quote path returned usable quote data.
- `error` - empty on success, bounded error text on failure.

Missing fields or missing timestamps are gate failures.

The observer also writes an optional JSON summary next to the CSV:

```text
data/processed/observer_latency_live_summary.json
```

The JSON summary is useful for quick inspection, but the CSV remains the source
for the gate evaluator.

## Smoke command

This validates only CSV plumbing. It must be reported as `SMOKE_ONLY`.

```powershell
py scripts\fast10_detector_emitter.py `
  --output data\processed\observer_latency_live.csv `
  --rows 1

py scripts\observer_gate_eval.py `
  --input data\processed\observer_latency_live.csv `
  --run-mode smoke
```

## Network-enabled observer command

Use observer credentials only. No wallet private key is required.

```powershell
$env:JUPITER_API_KEY = "..."

py scripts\fast10_observer.py `
  --input data\processed\fast10_live_candidates.csv `
  --output data\processed\observer_latency_live.csv `
  --summary-output data\processed\observer_latency_live_summary.json `
  --limit 100

py scripts\observer_gate_eval.py `
  --input data\processed\observer_latency_live.csv `
  --run-mode live `
  --min-live-rows 50
```

Input rows may be CSV or JSONL candidate rows from an upstream detector/replay
process. Minimum useful fields:

```text
signal_id
signal_chain_time
detected_local_time
token_mint
input_mint
output_mint
amount
slippage_bps
context_slot
volume_accel_10_300
```

Behavior:

- rows with `volume_accel_10_300 < 0.08807064065984926` are skipped;
- rows with `signal_pass=0/false/no` are skipped;
- rows with missing token mint or non-positive amount are skipped.

## Environment variables

```text
JUPITER_API_KEY=
JUPITER_BASE_URL=https://api.jup.ag/swap/v2
JUPITER_TAKER=
JUPITER_TIMEOUT_SECONDS=10
```

Notes:

- `JUPITER_API_KEY` is required by the current script because Jupiter Swap API V2 docs currently describe `x-api-key` access.
- `JUPITER_TAKER` is optional. It is not a private key.

## PASS gate

Observer PASS requires a real network-enabled run:

```text
row_count >= 50
coverage >= 90%
p50 total_latency_ms < 500
p90 total_latency_ms < 1000
p50/p90 quote_latency_ms populated
p50/p90 detector_latency_ms populated
no private keys
no live orders
complete audit log
```

## Package audit

Before accepting a ZIP delivery:

```powershell
py scripts\observer_package_audit.py C:\path\to\workspace.zip
```

PASS requires the required files, no pip cache/workspace noise, no secrets, and
SHA256 receipts for accepted artifacts.

## Boundaries

Status text may say `ACTIVE / GATE FAILED` after a network-enabled run fails
the thresholds. It must not imply live proof without raw latency rows.

Correct sequence:

```text
Observer smoke -> network observer -> gate report -> Paper discussion -> security review -> possible Live discussion
```

Live execution remains forbidden until a separate security review, private-key
boundary, slippage replay, fail-safe, and explicit approval.

# Observer Live-Run Runbook

## Current status

```text
ready-for-live-run / current gate failed
```

Canonical wording until a real network-enabled CSV exists:

```text
Observer harness validated; live network run pending.
```

Do not call this a live-alpha proof. Do not say the system is capturing live
signals unless `observer_latency_live.csv` was produced by a real
network-enabled run and evaluated by `scripts/observer_gate_eval.py`.

## Safety boundary

- Monitoring only.
- No private keys.
- No signing.
- No swap/send endpoints.
- No Paper mode before Gate 2 PASS.
- No Live execution before a separate security review and explicit approval.

## Mandatory latency CSV

`data/processed/observer_latency_live.csv` must contain these columns:

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

Missing columns or missing timestamp values are a gate failure.

## Gate 0: package integrity

Audit a delivery ZIP before accepting it:

```powershell
py scripts\observer_package_audit.py C:\path\to\observer-package.zip
```

PASS requires:

- `fast10_detector_emitter.py`
- `observer_gate_eval.py`
- `README_RUNBOOK.md`
- `observer_latency_live.csv`
- no pip cache or workspace noise
- no private keys, seed phrases, service-role keys, Dune/Helius/Jupiter secrets
- SHA256 receipt for accepted artifacts

## Gate 1: smoke plumbing

This validates the CSV path only. It is not a live network run.

```powershell
py scripts\fast10_detector_emitter.py `
  --output data\processed\observer_latency_live.csv `
  --rows 1

py scripts\observer_gate_eval.py `
  --input data\processed\observer_latency_live.csv `
  --run-mode smoke
```

Expected verdict:

```text
SMOKE_ONLY
```

## Gate 2: real network run

Use only observer credentials such as Jupiter/Helius API keys. Do not provide a
wallet private key.

```powershell
$env:JUPITER_API_KEY = "..."

py scripts\fast10_observer.py `
  --input data\processed\fast10_live_candidates.csv `
  --output data\processed\observer_latency_live.csv `
  --limit 100

py scripts\observer_gate_eval.py `
  --input data\processed\observer_latency_live.csv `
  --run-mode live `
  --min-live-rows 50
```

PASS minimum:

```text
coverage >= 90%
p50 total_latency_ms < 500
p90 total_latency_ms < 1000
p50/p90 quote_latency_ms populated
p50/p90 detector_latency_ms populated
```

## Gate 3: optimization branch

If quote latency dominates:

- keep-alive HTTP client
- async connection pool
- runner closer to RPC/Jupiter
- paid low-latency RPC
- prefilter before quote
- rough local quote pre-gate

If detector latency dominates:

- streaming JSONL append
- no pandas in hot path
- rolling in-memory windows
- async CSV writes
- optional Rust hot path

## Gate 4: decision boundary

Only after Gate 2 PASS can Paper mode be discussed.

Live execution remains forbidden until:

- private-key boundary is reviewed
- slippage replay is complete
- fail-safe behavior is specified
- security review passes
- explicit approval is given

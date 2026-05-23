# Fast10 Observer

## Purpose

This is the first live observer layer after the Fast10 execution lab.

It is **not** a trading bot.

The observer exists to answer one question:

```text
Can we detect a Fast10-compatible signal and get a Jupiter quote fast enough in real conditions?
```

## Current implementation status

Current repo implementation is a **no-key observer harness**:

- consumes detector-emitted signals from CSV or JSONL;
- filters Fast10-compatible rows using the current threshold;
- requests a live Jupiter quote using Swap API V2 `/order`;
- writes `observer_latency_live.csv`;
- writes `observer_latency_live_summary.json` with gate metrics and latency breakdown;
- prints PASS/FAIL latency summary.

What it does **not** do yet:

- compute Fast10 directly from raw websocket/Geyser flow;
- sign transactions;
- place orders;
- move funds.

## Why this shape is correct now

The lab already showed that the edge collapses near `0.5s` delay. Before building a faster execution path, we need a clean measurement path.

That means:

```text
signal -> detect -> quote request -> quote response -> parse -> CSV receipt
```

## Input contract

The observer script expects CSV or JSONL rows from an upstream detector or replay process.

Minimum useful fields:

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
- `JUPITER_TAKER` is optional. If omitted, the observer still requests quote/order data but does not produce a signable flow.

## Command

```bash
python scripts/fast10_observer.py \
  --input data/processed/fast10_live_candidates.csv \
  --output data/processed/observer_latency_live.csv
```

Optional:

```bash
python scripts/fast10_observer.py \
  --input data/processed/fast10_live_candidates.jsonl \
  --summary-output data/processed/observer_latency_live_summary.json \
  --limit 100
```

## Output

The script writes:

```text
data/processed/observer_latency_live.csv
data/processed/observer_latency_live_summary.json
```

CSV columns include:

```text
signal_id
token_mint
signal_chain_time
detected_local_time
quote_request_time
quote_response_time
quote_ready_time
signal_to_detect_ms
detect_to_request_ms
request_to_response_ms
response_to_parse_ms
detect_to_quote_ms
total_signal_to_quote_ms
quote_http_ms
quote_decode_ms
quote_total_ms
status
...
```

## Latency breakdown

The observer now emits stage-level latency so the team can see where the path fails:

- `signal_to_detect_ms` — chain timestamp to detector timestamp
- `detect_to_request_ms` — detector timestamp to HTTP request start
- `request_to_response_ms` — wall-clock HTTP request duration
- `response_to_parse_ms` — response arrival to payload parsed
- `detect_to_quote_ms` — detector timestamp to quote-ready time
- `total_signal_to_quote_ms` — chain timestamp to quote-ready time
- `quote_http_ms` — request-to-response measured by perf counter
- `quote_decode_ms` — JSON parse overhead measured by perf counter
- `quote_total_ms` — HTTP + decode measured by perf counter

## PASS gate

Observer PASS remains:

```text
p50 total_signal_to_quote_ms < 500
p90 total_signal_to_quote_ms < 1000
quote coverage >= 90%
no private keys
no live orders
complete audit log
```

## Current architectural split

### Already in repo

- `scripts/fast10_observer.py` — quote-latency harness with breakdown-aware summary
- Supabase/Streamlit bridge for storing and inspecting datasets
- execution-lab docs and verdict framing

### Still needed

- upstream live detector that emits Fast10 candidate rows;
- optional websocket/Geyser stream provider;
- first real network-enabled observer run;
- paper execution after latency PASS.

## Recommended next implementation

1. Build or connect a detector-emitter that writes `fast10_live_candidates.csv` or JSONL in real time.
2. Run `fast10_observer.py` against that feed in a network-enabled environment.
3. Save `observer_latency_live.csv` and `observer_latency_live_summary.json` into the existing app/Supabase path.
4. Produce a short PASS/FAIL receipt for Stas.

## Boundaries

Do not expand this observer into a trader before latency evidence is collected.

Correct sequence:

```text
Observer -> Paper -> Execution review -> only then discuss live trading
```
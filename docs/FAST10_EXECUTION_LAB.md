# Fast10 Execution Lab

## Purpose

This document defines the current execution-lab state for the `membot` research project.

The lab exists to answer one question:

```text
Can the Fast10 / Crescendo signal be observed, quoted, entered, and exited fast enough to survive real costs?
```

## Current signal

```text
Rule: crescendo_fast_10_p90
Threshold: volume_accel_10_300 >= 0.08807064065984926
Signals: 274 entry signals
Full market tape coverage: 267 evaluable / 274 total = 97.45%
```

## Current result

At `100 bps entry + 100 bps exit`:

```text
winrate = 48.31%
mean_net_pnl = +0.017119450 SOL
median_net_pnl = -0.005148431 SOL
sum_net_pnl = +4.570893168 SOL
```

This is a review state, not a production PASS.

## Exit rule sweep

Best current lab configuration:

```text
TP = +5%
SL = -20%
TS = 300s
mean = +0.009257
median = +0.040644
winrate = 0.582090
```

Interpretation: Fast10 is a micro-take candidate, not a moonshot strategy.

## Latency decay

The lab-model edge decays sharply at `0.5s` delay:

```text
0.0s mean +0.011386; winrate 0.490775
0.5s mean -0.004038; winrate 0.398524
```

## Required next artifact

```text
observer_latency_live.csv
```

Observer must not trade and must not contain private keys.

## Observer architecture

```text
StreamProvider -> Fast10Detector -> QuoteEngine -> LatencyRecorder -> CSV/DB
```

Components:

- StreamProvider: Yellowstone/Geyser-compatible transaction stream.
- Fast10Detector: computes live acceleration state.
- QuoteEngine: records quote and route metadata.
- LatencyRecorder: writes every timestamp.
- RiskGuard: blocks signing and private-key paths.

## Observer PASS

```text
p50 signal_to_quote_ms < 500
p90 signal_to_quote_ms < 1000
quote coverage >= 90%
no private keys
no live orders
complete audit log
```

## Paper Execution PASS

```text
median_net_pnl > 0
winrate > 50%
mean_net_pnl > 0
holds under slippage 50-100 bps
holds under measured latency
```

## Live policy

Live trading is forbidden until Observer and Paper both PASS.

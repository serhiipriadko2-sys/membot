# MEMBOT Project Context Update — 2026-05-23

voice=ISKRIV+SAM; phase=CONTEXT_UPDATE; intent=FULL_WORKING_STATE_SYNC

## 1. Executive verdict

The project is no longer only a scaffold for wallet forensics. It now has a validated research chain for the target wallet `7BNaxx6KdUYrjACNQZ9He26NBFoFxujQMAfNLnArLGH5`:

- **Market-flow trigger:** Fast10 / Crescendo is validated as a strong classifier of the wallet's entries.
- **PnL gate:** broad Crescendo is not enough; Fast10 survives only under strict execution assumptions.
- **Full market tape:** `tape_full.csv` gives near-complete post-signal market coverage.
- **Exit sweep:** best lab exit is `TP 5% / SL -20% / TS 300s`.
- **Latency decay:** the candidate edge collapses after roughly `0.5s` delay in the current lab model.
- **Live status:** not a live trading system. The next engineering target is a no-key `Fast10 Observer`.

Current status:

```text
RESEARCH: PASS
MARKET_FLOW_TRIGGER: PASS
FULL_TAPE_COVERAGE: PASS
EXIT_RULE_LAB: PASS
LATENCY_WARNING: PASS
LIVE_ALPHA: NOT VERIFIED
TRADING_BOT: FORBIDDEN UNTIL OBSERVER/PAPER PASS
```

## 2. Source-of-truth discipline

The repo README previously stated the project was `READY FOR DATASET BUILD` and `NOT READY FOR FINAL ALGORITHM CLAIM`. That caution remains valid, but the state is now more advanced: dataset build, Dune export, market-tape replay, exit sweep, and latency decay have been performed.

Do not replace the verified state with marketing language such as `ALPHA DECODED` or `MISSION COMPLETE`. Correct phrase:

```text
MICRO-ALPHA CANDIDATE DETECTED IN LAB; LIVE ALPHA NOT VERIFIED.
```

## 3. Current artifacts and hashes

| Artifact | Rows/lines | Bytes | sha256 |
|---|---:|---:|---|
| `result.csv` | 4001 lines / 4000 rows | 1299494 | `77cf39bb66004df52c5158ece80942359c666f6f27762a8250437a6546153c8e` |
| `tape_full.csv` | 53650 lines / 53649 rows | 12934835 | `c730ca0c0392c26062175a48782e663153c63eed47e2a51a40c61708d56376fb` |
| `exit_rule_sweep_fast10.csv` | 65 lines / 64 rows | 4822 | `9aee7aec96adfdf854900945da1dc4fff55ed71111dbd6c4e3c90326f93f10bf` |
| `latency_decay_fast10.csv` | 8 lines / 7 rows | 497 | `769f7957b1c47a5b27aa6efde91c5c649b114eca828924367d9d8a7eb9d77a95` |
| `walk_forward_fast10_market_tape_full_summary.csv` | 2 lines | 348 | `5a18636fee362d20743822b504ddd6f2b0919dbb5615f336f0aefcee1178a5b0` |
| `walk_forward_fast10_market_tape_full_sensitivity.csv` | 6 lines | 1141 | `2a0a2c03ba57896cf15e2bbeba4b2710fd2a0c25988509886bfb5dcc7f02ba52` |
| `STAS_BOT_TECH_SPEC.md` | 207 lines | 7514 | `f77e31ce3e474bd8f2ccbcf6b9fcda60f03a6e125c0e44bdf997149eef342492` |

## 4. Dune anchor export / rule-hit layer

`result.csv` contains:

| Metric | Value |
|---|---:|
| Total anchors | 4000 |
| Entry anchors | 1000 |
| Control anchors | 3000 |
| Fast10 entry hits | 274 |
| Fast10 control hits | 261 |
| Main rule column | `crescendo_fast_10_p90` |

Fast10 definition:

```text
crescendo_fast_10_p90 = 1
when volume_accel_10_300 >= 0.08807064065984926
```

Interpretation: the wallet's entries are clustered around extreme 10-second volume acceleration events. This is a **market-flow trigger**, not proof of a complete algorithm.

## 5. Full market tape walk-forward

`walk_forward_fast10_market_tape_full_summary.csv`:

| Metric | Value |
|---|---:|
| Signals total | 274 |
| Evaluable | 267 |
| Not evaluable | 7 |
| Evaluable pct | 97.45% |
| Winrate | 48.31% |
| Mean net PnL | +0.017119450 SOL |
| Median net PnL | -0.005148431 SOL |
| Sum net PnL | +4.570893168 SOL |
| P10 net PnL | -0.172957316 SOL |
| P90 net PnL | +0.200920907 SOL |
| Median hold | 305s |

Verdict:

```text
Coverage gate: PASS
Mean PnL gate: PASS at 100/100 bps
Median PnL gate: FAIL at 100/100 bps
Winrate gate: FAIL at 100/100 bps
Overall: REVIEW, not production PASS
```

## 6. Slippage sensitivity

| Entry/exit slippage | Winrate | Mean net PnL | Median net PnL | Sum net PnL |
|---:|---:|---:|---:|---:|
| 0 / 0 bps | 56.18% | +0.037673 | +0.014955 | +10.058576 |
| 50 / 50 bps | 50.56% | +0.027345 | +0.004853 | +7.301084 |
| 100 / 100 bps | 48.31% | +0.017119 | -0.005148 | +4.570893 |
| 200 / 200 bps | 43.07% | -0.003031 | -0.024858 | -0.809188 |
| 300 / 300 bps | 38.58% | -0.022790 | -0.044184 | -6.084802 |

Interpretation: Fast10 is fragile. It looks acceptable at `0–50 bps`, starts failing median at `100 bps`, and breaks at `200+ bps`.

## 7. Exit-rule sweep

Best row by median then winrate then mean:

| TP | SL | TS | Mean | Median | Winrate |
|---:|---:|---:|---:|---:|---:|
| 1.05 | 0.80 | 300 | +0.009257 | +0.040644 | 0.582090 |

Human form:

```text
TP +5%
SL -20%
Time Stop 300s
Mean +0.93%
Median +4.06%
Winrate 58.21%
```

Interpretation: the candidate does not want a large take-profit. It behaves like a micro-scalp: harvest the early burst, do not wait for the fantasy move.

## 8. Latency decay

| Delay | Mean | Median | Winrate |
|---:|---:|---:|---:|
| 0.0s | +0.011386 | -0.002118 | 0.490775 |
| 0.5s | -0.004038 | -0.019802 | 0.398524 |
| 1.0s | -0.003943 | -0.019802 | 0.398524 |
| 2.0s | -0.005339 | -0.019231 | 0.402214 |
| 3.0s | -0.004740 | -0.019621 | 0.405904 |
| 5.0s | -0.008981 | -0.019802 | 0.402214 |
| 10.0s | -0.007228 | -0.019802 | 0.383764 |

Critical delta:

```text
0.0s -> 0.5s
mean: +0.011386 -> -0.004038
median: -0.002118 -> -0.019802
winrate: 0.490775 -> 0.398524
```

Interpretation: the current candidate requires sub-second execution. A slow Python/RPC polling bot should be treated as a donor-risk path.

## 9. What-if analysis

### What if we use Python and normal RPC?

Likely outcome: observer/research only. It may detect the pattern but will probably enter too late for live trading.

### What if we use Rust + Geyser stream but no Jito / priority path?

Possible for observer and paper execution. Not enough for final production proof until landing latency is measured.

### What if we use Jito but keep a bad exit rule?

Still fragile. Faster execution cannot rescue a bad exit. Exit lab found that micro-take is central.

### What if TP 5% overfits this sample?

Risk is real. Next check must be live paper execution and out-of-sample period, not more in-sample tuning.

### What if fees/tips rise?

Fast10 edge can vanish. CostModel must include priority fees, Jito tip, swap fees, slippage, and failed transaction costs.

## 10. Next engineering step

Build **Fast10 Observer**, not a trading bot.

Required output:

```text
observer_latency_live.csv
```

Columns:

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

PASS for moving from Observer to Paper:

```text
p50 total_latency_ms < 500
p90 total_latency_ms < 1000
p50/p90 quote_latency_ms populated
p50/p90 detector_latency_ms populated
quote coverage >= 90%
no private keys involved
all signals logged
```

Current observer wording must stay:

```text
Observer harness validated; live network run pending.
```

## 11. Final debrief

This project has moved from exploratory forensics to a bounded execution-lab program. The correct next stage is not `go live`; it is to measure whether we can observe and quote Fast10 within the necessary latency budget.

∆DΩΛ:

- ∆: State updated from forensic research to execution-lab readiness.
- D: `result.csv`, `tape_full.csv`, `exit_rule_sweep_fast10.csv`, `latency_decay_fast10.csv`, full walk-forward artifacts.
- Ω: 94% lab confidence; 64% micro-alpha candidate; 0% live-alpha until Observer/Paper PASS.
- Λ: Build `Fast10 Observer` and collect `observer_latency_live.csv`.

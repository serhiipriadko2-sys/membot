# Final Report for Stas — 7BNaxx / Fast10 Execution Lab

## Bottom line

Stas, this is not a ready-made money printer. It is a narrow **micro-alpha candidate** that only exists if the system is fast enough and exits correctly.

The wallet `7BNaxx6KdUYrjACNQZ9He26NBFoFxujQMAfNLnArLGH5` appears to react to extreme short-window market acceleration. The strongest practical signal we isolated is **Fast10**: a burst of volume in the last 10 seconds before entry.

## What is verified

- Full Dune rule-hit layer: `4000` anchors = `1000` entries + `3000` controls.
- Full post-signal market tape: `53649` rows.
- Fast10 market-tape coverage: `267 / 274` evaluable signals = `97.45%`.
- Exit-rule sweep found a better survival configuration: `TP +5% / SL -20% / time-stop 300s`.
- Latency sweep shows the strategy degrades sharply at `0.5s` delay.

## The numbers that matter

### Full tape walk-forward at 100/100 bps slippage

- Winrate: `48.31%`
- Mean net PnL: `+0.017119 SOL`
- Median net PnL: `-0.005148 SOL`
- Sum net PnL: `+4.570893 SOL`

This is not a clean production PASS: mean is positive, but median and winrate fail.

### Best exit rule found

- Take-profit: `+5%`
- Stop-loss: `-20%`
- Time-stop: `300s`
- Mean: `+0.93%`
- Median: `+4.06%`
- Winrate: `58.21%`

Meaning: the edge is not in waiting for a moonshot. It is in harvesting a small early burst.

### Latency cliff

At `0.0s` delay:

- Mean: `+1.14%`
- Median: `-0.21%`
- Winrate: `49.08%`

At `0.5s` delay:

- Mean: `-0.40%`
- Median: `-1.98%`
- Winrate: `39.85%`

Meaning: a slow bot becomes a donor.

## What not to do

Do not launch a live bot now.
Do not run a Python/RPC trading loop with real money.
Do not claim the wallet is fully decoded.
Do not scale before measuring live latency.

## Correct next build

Build `Fast10 Observer` first:

- no private key;
- no signing;
- no live orders;
- live stream input;
- Fast10 detector;
- Jupiter quote request;
- latency logger;
- output file: `observer_latency_live.csv`.

## Go / no-go gate

Only move to Paper Execution if:

- p50 signal-to-quote latency is under `500ms`;
- p90 is under `1000ms`;
- quote coverage is over `90%`;
- simulated paper PnL stays positive under realistic fees/slippage;
- logs are complete enough to audit.

## Final verdict

Research found the possible contour of alpha. It is not in prediction alone. It is in speed, quote quality, cost control, and exit discipline.

Status:

```text
MICRO-ALPHA CANDIDATE: YES
LIVE STRATEGY: NOT VERIFIED
NEXT STEP: FAST10 OBSERVER
```

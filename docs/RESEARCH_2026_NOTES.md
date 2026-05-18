# Research 2026 Notes

## Status

This document summarizes the 2026 pre-buy trigger research package as research input only.
It does not upgrade any trigger to FACT or PASS.

Current verdict:

```text
research value: HIGH
SoT readiness: PARTIAL
trigger evidence: UNKNOWN until validation outputs exist
production claim: forbidden
```

## Main synthesis

The strongest conclusion is architectural:

```text
one secret trigger is unlikely
reject-first cascade is more plausible
```

Working engine shape:

```text
candidate universe
-> security / reject gates
-> regime router
-> entry context
-> trigger scores
-> execution feasibility
-> position sizing
```

## 2026 trigger families to track

### Implemented or partially implemented

- wallet_flow
- price_action
- repeat_wave
- cluster_context
- cross_chain_regime
- data_quality

### Planned / hypothesis-only

- vpin_toxicity
- graduation_crescendo
- token_2022_safety
- creator_fingerprint
- slot_execution
- liquidity_capacity
- attention_arbitrage
- entropy_compression
- reflexivity_feedback
- sybil_collapse

## H11-H14

### H11: VPIN / toxicity surge

Hypothesis: sustained buy/sell toxicity or order-flow imbalance before entry may separate entries from controls.

Required artifacts:
- market-wide trade buckets
- VPIN / OFI calculation
- entry-vs-control comparison
- delay/slippage validation

Current status: `HYPOTHESIS`.

### H12: Graduation / bonding-curve crescendo

Hypothesis: bonding-curve progress and acceleration near graduation may explain profitable entries.

Required artifacts:
- first trade time
- curve progress
- curve velocity / acceleration
- migration or graduation marker
- matched controls by age and liquidity bucket

Current status: `HYPOTHESIS`.

### H13: Regime-aware momentum

Hypothesis: fixed thresholds underperform thresholds conditioned on market regime.

Required artifacts:
- regime labels
- per-regime threshold evaluation
- OOS split
- latency/slippage replay

Current status: `HYPOTHESIS`.

### H14: Reflexivity / feedback inflection

Hypothesis: attention-driven feedback loops may explain memecoin acceleration better than raw momentum alone.

Required artifacts:
- attention / metadata / boost timeline
- price/volume reflexivity proxy
- controls matched by age, liquidity, and time

Current status: `HYPOTHESIS`.

## Immediate implementation direction

Do not add trading logic from this research package.

Do add:

- source audit rows
- manifest entries with `implemented: false`
- schema placeholders
- backlog tasks
- validation scripts

## Non-claims

The research package does not prove:

- trigger discovered
- copy-trading profitability
- exact wallet algorithm
- Jito or bundle use
- PumpSwap migration edge
- social/attention edge
- VPIN edge for this wallet

All such statements stay `UNKNOWN` until generated from reproducible project artifacts.

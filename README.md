# membot

Research scaffold for reverse-engineering and validating a high-frequency Solana meme-trading wallet.

Status:
- READY FOR DATASET BUILD
- READY FOR ENTRY-VS-CONTROL VALIDATION HARNESS
- NOT READY FOR FINAL ALGORITHM CLAIM
- NOT A TRADING BOT

## Purpose

This repository builds a reproducible forensic pipeline around raw Solana transaction data.
It is not a claim that the target wallet's algorithm has been decoded.

## Current target

Wallet:
- `7BNaxx6KdUYrjACNQZ9He26NBFoFxujQMAfNLnArLGH5`

Working hypotheses:
- H1: the wallet behaves like a short-horizon scalper.
- H2: a large part of the edge sits in ultra-small-cap setups.
- H3: a meaningful part of the edge comes from execution quality and low latency.
- H4: entries are driven by observable event triggers rather than random timing.

2026 research expansion:
- H11: VPIN / toxicity surge.
- H12: graduation / bonding-curve crescendo.
- H13: regime-aware momentum.
- H14: reflexivity / feedback inflection.

These are hypotheses until validated against controls.

## Source of truth

Do not use dashboard screenshots or third-party summaries as final truth.
Source of truth for claims in this repo should be:

1. Raw transaction exports.
2. Reproducible parsers and pairing logic.
3. Generated dataset artifacts.
4. Entry-vs-control validation reports.
5. Manual audit of ambiguous rows.
6. External dashboards only as hints, never as final proof.

## Pipeline layers

Core accounting:

```text
raw signatures
raw transactions
wallet_swaps.csv
trades_paired.csv
fee / inventory / latency reports
```

Pre-buy causality:

```text
price_series.csv
entry_context.csv
control_points.csv
trigger_tests.csv
cluster_context.csv
cross_chain_context.csv
cluster_trigger_tests.csv
cross_chain_trigger_tests.csv
```

Research discipline:

```text
source_audit -> feature_manifest -> schema contracts -> validation reports
```

## Current working documents

- `docs/PROTOCOL.md` — research protocol and evidence discipline.
- `docs/ENTRY_CONTEXT_PROTOCOL.md` — leakage-safe entry-context and controls.
- `docs/RESEARCH_2026_NOTES.md` — synthesis from the 2026 pre-buy report.
- `docs/SOURCE_AUDIT_2026.md` — source-audit register: verified / partial / pending.
- `docs/QC_FINDINGS.md` — current limitations and non-claims.
- `tasks/RESEARCH_BACKLOG_2026.md` — next tasks for research-grade validation.
- `configs/prebuy_feature_manifest.yaml` — implemented and planned features.
- `schemas/` — output contracts.

## Definition of done: trigger claim

A trigger claim is not accepted until it has:

- feature row in `configs/prebuy_feature_manifest.yaml`;
- schema coverage where applicable;
- `entry_context.csv` or context-specific equivalent;
- matched `control_points.csv` or derived control anchors;
- `trigger_tests.csv` / context-specific validation output;
- coverage report;
- explicit verdict: PASS / PARTIAL / NO_SIGNAL / UNKNOWN / FAIL;
- no use of future data;
- no production claim without out-of-sample, latency, fee, and slippage checks.

## Non-claims

This repository does not currently prove:

- exact algorithm logic;
- Jito bundle usage;
- block-order advantage;
- signal source provenance;
- social/off-chain signal provenance;
- final profitability under copied execution;
- any trigger discovered from the 2026 research report.

The preferred default is explicit `UNKNOWN`, not confident fiction.

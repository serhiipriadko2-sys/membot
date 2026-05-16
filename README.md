# membot

Research scaffold for reverse-engineering and validating a high-frequency Solana meme-trading wallet.

Status:
- READY FOR DATASET BUILD
- NOT READY FOR FINAL ALGORITHM CLAIM

## Purpose

This repository is for building a reproducible forensic pipeline around raw Solana transaction data.
It is not a claim that the target wallet's algorithm has been decoded.

## Research scope

Current target wallet:
- `7BNaxx6KdUYrjACNQZ9He26NBFoFxujQMAfNLnArLGH5`

Working hypotheses:
- H1: the wallet behaves like a short-horizon scalper.
- H2: a large part of the edge sits in ultra-small-cap setups.
- H3: a meaningful part of the edge comes from execution quality and low latency.
- H4: entries are driven by observable event triggers rather than random timing.

## Source of truth

Do not use dashboard screenshots or third-party summaries as final truth.
Source of truth for claims in this repo should be:
1. Raw transaction exports.
2. Reproducible parsers and pairing logic.
3. Report files generated from the dataset.
4. Manual audit of ambiguous rows.

## Initial structure

- `docs/PROTOCOL.md` — research protocol and evidence discipline.
- `docs/QC_FINDINGS.md` — current limitations and non-claims.
- `schemas/` — output schema notes.
- `scripts/` — future dataset and replay scripts.
- `tests/` — future validation fixtures and smoke tests.

## First definition of done

The first real milestone is not “algorithm solved”.
It is a reproducible dataset build with:
- raw signatures
- raw transactions
- normalized swap rows
- paired trades
- fee and tip signals
- latency sensitivity outputs
- a metrics report with explicit unknowns

## Non-claims

This repository does not currently prove:
- exact algorithm logic
- Jito bundle usage
- block-order advantage
- signal source provenance
- final profitability under copied execution

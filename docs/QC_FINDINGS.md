# QC Findings

Current state: scaffold plus partial pipeline groundwork.

## Hard non-claims

The repository does not currently prove:
- the exact trading algorithm
- Jito bundle inclusion
- block-order edge
- off-chain signal provenance
- final copy-trade profitability

## Current known-good areas

- README and protocol hold the correct research boundary.
- FIFO pairing exists as a first executable layer.
- Latency simulation now rejects impossible delayed entries.
- Slot-based delay is treated as slot progression, not as plus one second.
- Tests exist for latency timing and basic FIFO behavior.

## Current unknowns

- H3 latency decay is UNKNOWN until delayed-entry simulation uses a validated price series from a real dataset run.
- H4 signal edge is UNKNOWN until entry context and control-point event studies exist.
- Block-order is UNKNOWN until slot-level block mapping is implemented.
- Jito usage is UNKNOWN until evidence is stronger than static tip heuristics.
- End-to-end dataset coverage is UNKNOWN until fetch, normalize and report layers are run on real wallet data.

## Acceptance bar for first research-grade MVP

The first research-grade MVP should include:
- explicit dataset schema
- parser confidence flags
- pairing rules documented in plain language
- manual audit path for ambiguous rows
- metrics that degrade gracefully under missing enrichment
- tests for impossible or contradictory timing cases
- a real dataset run that produces explicit PASS, FAIL or UNKNOWN markers

## Why this file exists

This file is here to stop the project from drifting into claims before the data path is trustworthy.

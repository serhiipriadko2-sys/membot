# QC Findings

Current state: scaffold only.

## Hard non-claims

The repository does not currently prove:
- the exact trading algorithm
- Jito bundle inclusion
- block-order edge
- off-chain signal provenance
- final copy-trade profitability

## Current unknowns

- H3 latency decay is UNKNOWN until delayed-entry simulation uses a validated price series and rejects impossible post-exit entries.
- H4 signal edge is UNKNOWN until entry context and control-point event studies exist.
- Block-order is UNKNOWN until slot-level block mapping is implemented.
- Jito usage is UNKNOWN until evidence is stronger than static tip heuristics.

## Acceptance bar for first research-grade MVP

The first research-grade MVP should include:
- explicit dataset schema
- parser confidence flags
- pairing rules documented in plain language
- manual audit path for ambiguous rows
- metrics that degrade gracefully under missing enrichment
- tests for impossible or contradictory timing cases

## Why this file exists

This file is here to stop the project from drifting into claims before the data path is trustworthy.

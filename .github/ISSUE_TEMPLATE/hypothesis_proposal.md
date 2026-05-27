---
name: Hypothesis Proposal
about: Propose a new entry/exit hypothesis to test
title: '[HYPOTHESIS] '
labels: hypothesis, research
assignees: ''
---

## Hypothesis Type
- [ ] Entry hypothesis
- [ ] Exit hypothesis
- [ ] Context enrichment
- [ ] Other (describe below)

## Feature Definition

**Feature name:** `your_feature_name`

**Description:** Clear explanation of what this feature measures and why it might be predictive.

**Thresholds:**
- Minimum: [value or "none"]
- Maximum: [value or "none"]
- Expected direction: [above_min / below_max / inside_range / bool_expected]

**Required columns:** List of column names needed in entry_context.csv

## Rationale
Why do you believe this feature will separate winners from losers? Include:
- Theoretical basis
- Observations from wallet behavior
- Analogous patterns in other markets

## Test Plan

### Data requirements
- [ ] Can be tested on existing entry_context.csv
- [ ] Requires new raw data collection
- [ ] Needs market-wide context (Dune/Helius)

### Statistical tests
- [ ] Kolmogorov-Smirnov (distribution)
- [ ] Mann-Whitney U (median difference)
- [ ] Effect size calculation (Cohen's d)
- [ ] Other: _____

### Success criteria
What would constitute PASS, FAIL, or PARTIAL support?

## Implementation Notes
Suggested approach for implementing this test in the pipeline.

## References
Link to relevant documentation, prior research, or external resources.

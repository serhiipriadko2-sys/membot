# Hypothesis Status Matrix

## Overview

This document tracks the validation status of all entry and exit hypotheses in the membot research project.

**Last updated:** 2026-05-27  
**Status legend:**  
- ✅ PASS — Hypothesis supported by data (not proven)  
- ❌ FAIL — Hypothesis contradicted by data  
- ⚠️ PARTIAL — Mixed evidence, needs more data  
- 🔍 UNTESTED — Not yet evaluated  
- 📊 RAW_REQUIRED — Requires raw on-chain or market context columns  
- 🧪 SYNTHETIC — Tested on synthetic fixtures only  

---

## Entry Hypotheses

| Hypothesis | Feature | Min | Max | Direction | Status | Evidence | Notes |
|------------|---------|-----|-----|-----------|--------|----------|-------|
| H1 | market_cap_usd | $5K | $85K | inside_range | 🔍 UNTESTED | None | Ultra-small-cap sweet spot hypothesis |
| H2 | liquidity_usd | $2K | — | above_min | 🔍 UNTESTED | None | Minimum liquidity for entry/exit |
| H3 | token_age_seconds | 10s | 900s | inside_range | 🔍 UNTESTED | None | Early-life window (10s to 15min) |
| H4 | volume_velocity_tps | 3 | — | above_min | 🔍 UNTESTED | None | Crowd/liquidity activity threshold |
| H5 | mint_authority_revoked | true | — | bool_expected | 📊 RAW_REQUIRED | None | Anti-rug filter |
| H6 | freeze_authority_revoked | true | — | bool_expected | 📊 RAW_REQUIRED | None | Anti-rug filter |
| H7 | lp_locked | true | — | bool_expected | 📊 RAW_REQUIRED | None | LP lock safety filter |
| H8 | top10_holders_percent | — | 70% | below_max | 🔍 UNTESTED | None | Concentration risk filter |

---

## Exit Hypotheses

| Hypothesis | Feature | Min | Max | Direction | Status | Evidence | Notes |
|------------|---------|-----|-----|-----------|--------|----------|-------|
| E1 | take_profit_percent | 5% | 50% | target_range | ⚠️ PARTIAL | Exit-rule lab | Best results at +5% TP |
| E2 | stop_loss_percent | -20% | -5% | target_range | ⚠️ PARTIAL | Exit-rule lab | Best results at -20% SL |
| E3 | time_stop_seconds | 300s | 1800s | target_range | ⚠️ PARTIAL | Exit-rule lab | 300s time stop optimal |
| E4 | trailing_stop_percent | 10% | 40% | target_range | 🔍 UNTESTED | None | Trailing stop hypothesis |
| E5 | volume_decay_threshold | 0.3 | 0.7 | inside_range | 🔍 UNTESTED | None | Exit on volume decay |
| E6 | liquidity_collapse | -50% | — | below_threshold | 🔍 UNTESTED | None | Exit on liquidity drop |

---

## Fast10 Micro-Alpha Candidate

| Component | Status | Threshold | Notes |
|-----------|--------|-----------|-------|
| Signal detection | ✅ PASS | 10-sec volume acceleration p90 | Full tape tested |
| Market coverage | ✅ PASS | 97.45% | 267/274 signals evaluable |
| Walk-forward (100/100 bps) | ⚠️ PARTIAL | mean +, median - | Slippage sensitivity |
| Best exit rule | ⚠️ PARTIAL | TP +5%, SL -20%, TS 300s | Median +4.06%, WR 58.21% |
| Latency cliff | ⚠️ WARNING | ~0.5s | Edge breaks beyond this |
| Live alpha | 🔍 NOT VERIFIED | — | Requires Observer validation |

**Conclusion:** MICRO-ALPHA CANDIDATE DETECTED IN LAB; LIVE ALPHA NOT VERIFIED

---

## Cluster Context Hypotheses

| Hypothesis | Feature | Status | Evidence | Notes |
|------------|---------|--------|----------|-------|
| C1 | wallet_cluster_correlation | 🔍 UNTESTED | None | Coordinated wallet detection |
| C2 | same_token_cluster_activity | 🔍 UNTESTED | None | Multi-wallet same-token plays |
| C3 | cluster_entry_timing | 🔍 UNTESTED | None | Leader-follower patterns |

---

## Cross-Chain Context Hypotheses

| Hypothesis | Feature | Status | Evidence | Notes |
|------------|---------|--------|----------|-------|
| X1 | eth_bridge_flow | 🔍 UNTESTED | None | ETH->SOL bridge correlation |
| X2 | stablecoin_regime | 🔍 UNTESTED | None | USDC/USDT flow regime |
| X3 | cross_chain_sentiment | 🔍 UNTESTED | None | Social sentiment correlation |

---

## Market-Wide Context Hypotheses

| Hypothesis | Feature | Status | Evidence | Notes |
|------------|---------|--------|----------|-------|
| M1 | market_same_token_swaps | 🔍 UNTESTED | None | Dune market-wide same-token activity |
| M2 | dex_volume_correlation | 🔍 UNTESTED | None | DEX-wide volume correlation |
| M3 | competitor_entry_density | 🔍 UNTESTED | None | Competing bot entry density |

---

## Required Actions

### P0 — Critical
- [ ] Calibrate H1-H8 thresholds on real wallet data
- [ ] Complete raw data collection for H5-H7 (mint/freeze authority, LP lock)
- [ ] Run full entry-vs-control tests on market-enriched dataset

### P1 — High
- [ ] Validate E1-E3 exit rules on out-of-sample data
- [ ] Test E4-E6 exit hypotheses
- [ ] Complete Observer live-run for Fast10 latency validation

### P2 — Medium
- [ ] Build cluster context pipeline (C1-C3)
- [ ] Integrate cross-chain data sources (X1-X3)
- [ ] Expand Dune market context queries (M1-M3)

---

## References

- `configs/entry_exit_hypotheses.v0.yaml` — Hypothesis configuration
- `docs/FAST10_EXECUTION_LAB.md` — Fast10 execution lab protocol
- `reports/STAS_FINAL_REPORT_7BN.md` — Handoff report with initial findings
- `scripts/20_test_entry_triggers.py` — Entry trigger test script
- `scripts/29_test_market_triggers.py` — Market trigger test script

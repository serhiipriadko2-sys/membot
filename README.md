# membot

Research scaffold for reverse-engineering and validating a high-frequency Solana meme-trading wallet.

## Current status — 2026-05-23

```text
RESEARCH: PASS
MARKET_FLOW_TRIGGER: PASS
FULL_TAPE_COVERAGE: PASS
EXIT_RULE_LAB: PASS
LATENCY_WARNING: PASS
LIVE_ALPHA: NOT VERIFIED
TRADING_BOT: FORBIDDEN UNTIL OBSERVER/PAPER PASS
```

This repository is not a trading bot. It is a forensic and execution-lab workspace.

## Current target

Wallet:

```text
7BNaxx6KdUYrjACNQZ9He26NBFoFxujQMAfNLnArLGH5
```

## Current strongest conclusion

The strongest current candidate is `crescendo_fast_10_p90`, also called **Fast10**.

It identifies extreme 10-second volume acceleration before entry. Full market-tape testing shows the signal is a plausible micro-alpha candidate only if execution is very fast and the exit rule is strict.

Correct wording:

```text
MICRO-ALPHA CANDIDATE DETECTED IN LAB; LIVE ALPHA NOT VERIFIED.
```

Do not use:

```text
ALPHA DECODED
MISSION COMPLETE
READY TO TRADE
```

## Key evidence

| Layer | Current result |
|---|---:|
| Rule-hit export | 4000 anchors = 1000 entries + 3000 controls |
| Fast10 signals | 274 |
| Full post-signal market tape | 53649 rows |
| Full tape evaluable coverage | 267 / 274 = 97.45% |
| Walk-forward at 100/100 bps | mean positive, median negative |
| Best exit-rule lab row | TP +5%, SL -20%, TS 300s |
| Best exit-rule median | +4.06% |
| Best exit-rule winrate | 58.21% |
| Latency cliff | edge breaks at ~0.5s in current lab model |

## Working documents

- `reports/PROJECT_CONTEXT_UPDATE_2026-05-23.md` — current source-of-truth update.
- `reports/STAS_FINAL_REPORT_7BN.md` — handoff report for Stas.
- `docs/FAST10_EXECUTION_LAB.md` — execution-lab protocol and gates.
- `docs/FAST10_OBSERVER.md` — no-key observer workflow and input/output contract.
- `docs/SUPABASE_SYNC_STATUS.md` — Supabase migration/sync status.
- `supabase/migrations/20260523000000_execution_lab_research_registry.sql` — proposed metadata registry migration.
- `scripts/fast10_observer.py` — observer harness for signal -> Jupiter quote latency.
- `reports/research_dossier_2026-05-22.md` — earlier audit dossier.

## Source of truth

Do not use dashboard screenshots or third-party summaries as final truth. Source of truth for claims in this repo should be:

1. Raw transaction exports.
2. Reproducible parsers and pairing logic.
3. Generated dataset artifacts.
4. Entry-vs-control validation reports.
5. Market-tape walk-forward results.
6. Exit-rule and latency-decay sweeps.
7. Manual audit of ambiguous rows.
8. External dashboards only as hints, never as final proof.

## Next step

Build **Fast10 Observer**:

```text
live stream -> Fast10 detect -> quote -> latency log -> observer_latency_live.csv
```

Current repo status:

```text
observer harness: READY
live detector-emitter: NEXT
paper execution: BLOCKED UNTIL OBSERVER PASS
```

No private key. No signing. No live trading.

Current command:

```bash
python scripts/fast10_observer.py \
  --input data/processed/fast10_live_candidates.csv \
  --output data/processed/observer_latency_live.csv
```

PASS for moving to Paper Execution:

```text
p50 signal_to_quote_ms < 500
p90 signal_to_quote_ms < 1000
quote coverage >= 90%
no private keys
complete audit log
```

## Non-claims

This repository does not currently prove:

- exact target-wallet algorithm;
- Jito bundle usage by the target wallet;
- final profitability under copied execution;
- live execution edge;
- safety of real-money deployment;
- production readiness.

The preferred default is explicit `UNKNOWN`, not confident fiction.

# Source Audit 2026

## Purpose

Track every external claim before it becomes project evidence.

Statuses:

- `VERIFIED`: primary source or official documentation checked.
- `PARTIAL`: source exists, but interpretation, recency, or applicability still needs review.
- `PENDING`: claim exists in research notes, but no source audit has been completed.
- `REJECTED`: source does not support the claim.

## Audit rows

| ID | Claim | Source class | URL / source | Status | Project use |
|---|---|---|---|---:|---|
| SRC-001 | Solana `getTransaction` provides slot, block time, transaction, and metadata useful for forensic tx parsing. | Official docs | https://solana.com/docs/rpc/http/gettransaction | VERIFIED | Raw transaction parsing / wallet swaps |
| SRC-002 | Solana `getBlock` can provide block-level transaction context and is useful for slot/order analysis. | Official docs | https://solana.com/docs/rpc/http/getblock | VERIFIED | Narrow execution / slot context only |
| SRC-003 | Dune `dex_solana.trades` can support market-wide Solana DEX trade context; multi-hop rows require careful grouping. | Official docs | https://docs.dune.com/data-catalog/curated/dex-trades/solana/solana-dex-trades | VERIFIED | Market context enrichment |
| SRC-004 | Jito bundles and tip accounts are relevant to execution-layer research. | Official docs | https://docs.jito.wtf/lowlatencytxnsend/ | VERIFIED | Execution context / latency research |
| SRC-005 | DEX Screener exposes token profile, boosts, orders, pair/token data and rate-limited API endpoints. | Official docs | https://docs.dexscreener.com/api/reference | VERIFIED | Metadata/liquidity/attention enrichment |
| SRC-006 | Pump.fun graduation can be modeled as a prediction problem using bonding-curve features. | Academic paper | arXiv Pump.fun graduation research | PARTIAL | H12 graduation-crescendo hypothesis |
| SRC-007 | Solana rug-pull detection benefits from transaction/state behavior and organized-group analysis. | Academic paper | SolRugDetector / arXiv | PARTIAL | Anti-rug / cluster toxicity design |
| SRC-008 | Helius Enhanced Transactions API is deprecated in favor of LaserStream. | Vendor docs / claim in PDF | pending direct official verification | PENDING | Do not use as SoT yet |
| SRC-009 | LaserStream is about 200ms faster than older alternatives. | Vendor benchmark claim | pending direct official verification | PENDING | Do not use as SoT yet |
| SRC-010 | PumpSwap replaced Raydium as the primary pump.fun migration target. | Industry / platform claim | pending direct official verification | PENDING | Backlog only |
| SRC-011 | Token-2022 extensions such as PermanentDelegate, TransferHook, and ConfidentialTransfer add new risk flags. | Official docs needed | pending direct official verification | PENDING | Backlog only |
| SRC-012 | RugCheck insider-network tooling is a gold standard for screening. | Industry claim | pending direct official verification | PENDING | Backlog only |
| SRC-013 | Jito ShredStream or similar stream gives minimum-latency data edge. | Vendor docs / benchmark claim | pending direct official verification | PENDING | Backlog only |
| SRC-014 | VPIN predicts crypto price jumps. | Academic paper claim | pending paper audit | PENDING | H11 only |
| SRC-015 | HMM / NHMM regime detection improves crypto trading thresholds. | Academic paper claim | pending paper audit | PENDING | H13 only |
| SRC-016 | Entropy filtering improves ML signal stability. | Academic paper claim | pending paper audit | PENDING | Entropy hypothesis only |
| SRC-017 | Cross-chain Sybil detection outperforms single-chain detection. | Academic paper claim | pending paper audit | PENDING | Cluster / sybil backlog |

## Usage rule

Only `VERIFIED` and carefully scoped `PARTIAL` rows can be cited as project basis.
`PENDING` rows may appear in backlog or feature manifest with:

```yaml
implemented: false
status: HYPOTHESIS
requires_source_audit: true
```

## Current conclusion

The 2026 PDF improves the research map but does not prove any pre-buy trigger for the target wallet.

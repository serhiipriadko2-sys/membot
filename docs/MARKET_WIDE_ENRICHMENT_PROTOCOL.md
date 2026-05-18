# Market-Wide Enrichment Protocol

## Goal

Move beyond wallet-derived context by adding market-wide pre-entry context.

The previous M3 dense run showed:

```text
feature_coverage_pct: PASS
wallet_flow hints: weak/moderate
cluster context: UNKNOWN
cross-chain context: UNKNOWN/NO_SIGNAL
```

This means the next research-grade step is not another wallet-only run. It is a
market-wide enrichment layer.

## Data sources

### Dune / DEX trade export

Use a local export of Solana DEX trades, such as Dune `dex_solana.trades` or an
equivalent export.

Expected fields can vary, so scripts accept aliases for:

```text
block_time / timestamp
tx_id / signature
block_slot / slot
token_bought_mint_address
token_sold_mint_address
amount_usd / volume_usd
trader_id / wallet / buyer / seller
```

Multi-hop swaps may appear as multiple rows. Do not treat row count as trade
count without grouping by transaction when making final claims.

### Helius enrichment

`28_build_helius_enrichment.py` parses a local Helius Enhanced Transactions JSON
export. It does not call Helius directly and does not read API keys.

Use it for:

```text
fee_lamports
slot
timestamp
native_transfer_count
token_transfer_count
token_balance_change_count
```

Helius product/deprecation/status claims must stay in `docs/SOURCE_AUDIT_2026.md`
until verified from official docs.

## New scripts

```text
25_build_market_context.py
26_build_market_controls.py
27_enrich_entry_context_market.py
28_build_helius_enrichment.py
```

## Runtime order

Given:

```text
data/processed/entry_context.csv
data/processed/control_points.csv
data/processed/dune_solana_trades.csv
```

Run:

```bash
python scripts/25_build_market_context.py --include-controls
python scripts/26_build_market_controls.py
python scripts/27_enrich_entry_context_market.py
```

Optional Helius local export:

```bash
python scripts/28_build_helius_enrichment.py \
  --input data/processed/helius_enhanced_transactions.json
```

## Outputs

```text
data/processed/market_context.csv
data/processed/market_control_points.csv
data/processed/entry_context_market_enriched.csv
data/processed/helius_enrichment.csv
```

## Guardrails

- No API keys in repo.
- No live RPC calls in enrichment scripts.
- No fake market rows.
- Missing market export means UNKNOWN, not zero evidence.
- Cross-chain remains regime context, not token-specific BUY proof.
- Cluster presence remains context, not alpha.
- Dune rows are not automatically trades when multi-hop routing exists.

## Acceptance criteria

Market-wide enrichment is considered dataset-ready when:

- `market_context.csv` exists for entries and controls.
- Coverage is reported per window.
- Market controls exist for a meaningful share of entries.
- Market features are tested against controls.
- Claims remain PARTIAL until OOS and latency/fee/slippage validation.

## Non-claim

This protocol does not prove H4, H11, H12, H13, or H14. It creates the missing
data layer required to test them.

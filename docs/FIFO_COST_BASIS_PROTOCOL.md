# FIFO cost basis protocol

Status: bridge layer for open inventory accounting.

## Purpose

Reconcile current open-position balances against normalized historical buy/sell lots and produce FIFO-derived cost-basis fields.

This layer must not promote Solscan current value, GMGN unrealized PnL, or pro-rata estimates into verified accounting.

## Inputs

```text
data/processed/open_positions.csv
data/processed/trades_normalized.csv
```

`open_positions.csv` is current inventory. It may come from Solscan UI, Solana RPC `getTokenAccountsByOwner`, or another portfolio export.

`trades_normalized.csv` is historical trade flow. It must include enough history to cover the currently open lots.

Minimum trade fields:

```text
timestamp,tx_hash,token_mint,token_symbol,side,token_amount,usd_amount,fee_usd
```

## Outputs

```text
data/processed/open_positions_fifo_verified.csv
```

Added fields:

```text
verified_fifo_cost_basis_usd
verified_fifo_unrealized_pnl_usd
verified_fifo_unrealized_pnl_pct
fifo_matched_open_amount
fifo_coverage_pct
fifo_status
cost_basis_status
fifo_notes
```

## Status values

```text
verified_fifo_full
partial_fifo_coverage
no_fifo_match
no_position_balance
```

`cost_basis_status = FIFO_VERIFIED` is allowed only when `fifo_status = verified_fifo_full`.

Partial coverage must stay `PARTIAL_FIFO`.

No matching lots must stay `UNKNOWN`.

## Guardrails

- Do not estimate missing lots.
- Do not call pro-rata allocation verified.
- Do not use current value as cost basis.
- Preserve negative unrealized PnL.
- If 90D history is insufficient, extend the export window instead of inventing history.
- Multi-hop / aggregator rows require `tx_hash` audit before claims.
- `fee_usd = 0` is not verified fee accounting unless fee source is explicitly audited.

## Method

1. Sort normalized trades by timestamp.
2. Add buy lots to a FIFO queue per token mint.
3. Consume FIFO lots on sells.
4. Match current open balance against the remaining FIFO lots.
5. Calculate cost basis only for the matched portion.
6. Mark full / partial / missing coverage explicitly.

## Interpretation

`verified_fifo_unrealized_pnl_usd` is useful only with sufficient `fifo_coverage_pct` and correct mint normalization.

For old wallets, a 90D trade export may be incomplete. If current positions were opened before the export window, the correct output is `partial_fifo_coverage` or `no_fifo_match`, not a guessed cost basis.

-- Dune SQL template: market-wide same-token swaps for M3.2
--
-- Goal:
--   Export DEX trades around mints observed in entry_context.csv, then normalize with:
--   python scripts/21_build_market_same_token_swaps.py --input dune_market_same_token_swaps.csv
--
-- Notes:
--   1. Replace the VALUES list with token mints from data/processed/entry_context.csv.
--   2. Set the time window around your sample period.
--   3. dex_solana.trades may contain multiple rows for multi-hop swaps. Do not use this
--      output as final accounting PnL without tx-level grouping/audit.

with target_mints(token_mint) as (
    values
        -- ('TOKEN_MINT_1'),
        -- ('TOKEN_MINT_2')
        ('REPLACE_WITH_TOKEN_MINT')
),
raw as (
    select
        block_time,
        block_slot,
        tx_id,
        trader_id,
        project,
        trade_source,
        token_bought_mint_address,
        token_bought_symbol,
        token_bought_amount,
        token_sold_mint_address,
        token_sold_symbol,
        token_sold_amount,
        amount_usd
    from dex_solana.trades
    where block_time >= timestamp '2026-05-01 00:00:00'
      and block_time <  timestamp '2026-05-19 00:00:00'
      and (
        token_bought_mint_address in (select token_mint from target_mints)
        or token_sold_mint_address in (select token_mint from target_mints)
      )
)
select *
from raw
order by block_time asc, block_slot asc, tx_id asc;

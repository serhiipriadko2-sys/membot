-- M3 Market-Wide Solana DEX Export
--
-- Purpose:
--   Export market-wide same-token trades around the 40 entry anchors and
--   120 control anchors used by the M3 validation run.
--
-- Output target:
--   data/processed/dune_solana_trades.csv
--
-- Guardrails:
--   - This export is context data, not final proof of a trigger.
--   - Multi-hop swaps may appear as multiple rows. Group by tx_id when making
--     final trade-count claims.
--   - Replace the VALUES blocks with the real token mints and time bounds from
--     entry_context.csv / control_points.csv.
--
-- Expected columns consumed by scripts/25_build_market_context.py:
--   block_time, block_slot, tx_id, token_bought_mint_address,
--   token_sold_mint_address, amount_usd, token_bought_amount,
--   token_sold_amount, token_bought_symbol, token_sold_symbol,
--   trader_id, project, version

WITH target_mints(mint) AS (
    VALUES
        -- Replace with exact 16 token mints from entry_context.csv.
        -- ('MINT_1'),
        -- ('MINT_2')
        ('REPLACE_WITH_TOKEN_MINT')
),
anchor_bounds AS (
    SELECT
        -- Replace with min(anchor_time) - interval '30 minutes'.
        TIMESTAMP '2026-05-17 00:00:00' AS start_time,
        -- Replace with max(entry_time/control_time) + interval '5 minutes'.
        TIMESTAMP '2026-05-18 00:00:00' AS end_time
),
raw AS (
    SELECT
        block_time,
        block_slot,
        tx_id,
        project,
        version,
        token_bought_mint_address,
        token_sold_mint_address,
        token_bought_symbol,
        token_sold_symbol,
        token_bought_amount,
        token_sold_amount,
        amount_usd,
        trader_id
    FROM dex_solana.trades
    WHERE block_time >= (SELECT start_time FROM anchor_bounds)
      AND block_time <= (SELECT end_time FROM anchor_bounds)
      AND (
          token_bought_mint_address IN (SELECT mint FROM target_mints)
          OR token_sold_mint_address IN (SELECT mint FROM target_mints)
      )
)
SELECT *
FROM raw
ORDER BY block_time, block_slot, tx_id;

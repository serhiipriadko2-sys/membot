#!/usr/bin/env python3
"""Render a ready-to-paste Dune SQL query from entry_context.csv mints.

This removes the manual error-prone step of copying token mints into
sql/dune_market_same_token_swaps.sql.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from common import DATA_PROCESSED, read_csv

DEFAULT_OUTPUT = Path("data/external/dune_market_same_token_swaps_rendered.sql")


def quote_sql(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def parse_ts(value: str) -> int:
    if not value:
        return 0
    try:
        return int(float(value))
    except ValueError:
        return 0


def utc_sql(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def extract_mints_and_window(rows: list[dict[str, str]], pad_seconds: int) -> tuple[list[str], str, str]:
    mints = sorted({str(row.get("token_mint") or "") for row in rows if row.get("token_mint")})
    times = [parse_ts(str(row.get("entry_time") or row.get("control_time") or "")) for row in rows]
    times = [ts for ts in times if ts > 0]
    if times:
        start = min(times) - pad_seconds
        end = max(times) + pad_seconds
    else:
        now = datetime.now(tz=timezone.utc)
        start = int((now - timedelta(days=7)).timestamp())
        end = int(now.timestamp())
    return mints, utc_sql(start), utc_sql(end)


def values_clause(mints: Iterable[str]) -> str:
    lines = [f"        ({quote_sql(mint)})" for mint in mints]
    if not lines:
        lines = ["        ('REPLACE_WITH_TOKEN_MINT')"]
    return ",\n".join(lines)


def render_sql(mints: list[str], start_time: str, end_time: str) -> str:
    return f"""-- Rendered by scripts/24_render_dune_market_query.py
-- Mints: {len(mints)}
-- Window UTC: {start_time} -> {end_time}
-- Warning: dex_solana.trades may contain multi-hop legs. Use for market-flow context;
-- do not use as final accounting PnL without tx-level grouping/audit.

with target_mints(token_mint) as (
    values
{values_clause(mints)}
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
    where block_time >= timestamp '{start_time}'
      and block_time <  timestamp '{end_time}'
      and (
        token_bought_mint_address in (select token_mint from target_mints)
        or token_sold_mint_address in (select token_mint from target_mints)
      )
)
select *
from raw
order by block_time asc, block_slot asc, tx_id asc;
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Render Dune SQL with target mints from entry/control context")
    parser.add_argument("--context", default=str(DATA_PROCESSED / "entry_context.csv"))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--pad-seconds", type=int, default=600, help="Time padding before first and after last entry/control anchor")
    args = parser.parse_args()

    rows = read_csv(Path(args.context))
    mints, start_time, end_time = extract_mints_and_window(rows, args.pad_seconds)
    sql = render_sql(mints, start_time, end_time)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(sql, encoding="utf-8")
    print(f"[OK] wrote {output} with {len(mints)} token mints, window {start_time} -> {end_time}")


if __name__ == "__main__":
    main()

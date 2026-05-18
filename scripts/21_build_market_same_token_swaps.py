#!/usr/bin/env python3
"""Build market_same_token_swaps.csv from external DEX trade exports.

M3.2 scope:
- start with imported CSV exports rather than expensive live RPC scans;
- normalize market-wide same-token trade rows into one schema;
- keep provenance/source fields explicit;
- do not fabricate market-wide data if no source CSV exists.

Recommended upstream sources:
- Dune dex_solana.trades export for token mints and time windows of interest;
- future Helius/DexScreener enrichment exports.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import DATA_PROCESSED, ensure_dirs, read_csv, write_csv, as_float, as_int

FIELDS = [
    "block_time",
    "block_time_utc",
    "block_slot",
    "tx_hash",
    "token_mint",
    "token_symbol",
    "side",
    "trader",
    "amount_token",
    "amount_sol",
    "amount_usd",
    "price_usd",
    "project",
    "trade_source",
    "source_file",
    "source_schema",
    "parse_confidence",
    "notes",
]

SOL_MINTS = {
    "So11111111111111111111111111111111111111112",
    "So11111111111111111111111111111111111111111",
}
USDC_MINTS = {
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
}
QUOTE_MINTS = SOL_MINTS | USDC_MINTS


def first(row: dict[str, str], *names: str) -> str:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return str(value)
    return ""


def normalize_side_and_token(row: dict[str, str]) -> tuple[str, str, str, float]:
    bought_mint = first(row, "token_bought_mint_address", "token_bought_mint", "bought_mint")
    sold_mint = first(row, "token_sold_mint_address", "token_sold_mint", "sold_mint")
    bought_symbol = first(row, "token_bought_symbol", "bought_symbol")
    sold_symbol = first(row, "token_sold_symbol", "sold_symbol")
    bought_amount = as_float(first(row, "token_bought_amount", "bought_amount"), 0.0)
    sold_amount = as_float(first(row, "token_sold_amount", "sold_amount"), 0.0)

    if bought_mint and sold_mint:
        if bought_mint not in QUOTE_MINTS and sold_mint in QUOTE_MINTS:
            return "BUY", bought_mint, bought_symbol, bought_amount
        if sold_mint not in QUOTE_MINTS and bought_mint in QUOTE_MINTS:
            return "SELL", sold_mint, sold_symbol, sold_amount
        if bought_mint not in QUOTE_MINTS:
            return "BUY", bought_mint, bought_symbol, bought_amount
        if sold_mint not in QUOTE_MINTS:
            return "SELL", sold_mint, sold_symbol, sold_amount

    side = first(row, "side", "swap_side").upper()
    mint = first(row, "token_mint", "mint")
    symbol = first(row, "token_symbol", "symbol")
    amount = as_float(first(row, "token_amount", "amount_token"), 0.0)
    return side or "UNKNOWN", mint, symbol, amount


def estimate_sol_amount(row: dict[str, str]) -> float:
    sol_amount = as_float(first(row, "amount_sol", "sol_amount"), 0.0)
    if sol_amount > 0:
        return sol_amount
    bought_mint = first(row, "token_bought_mint_address", "token_bought_mint", "bought_mint")
    sold_mint = first(row, "token_sold_mint_address", "token_sold_mint", "sold_mint")
    if bought_mint in SOL_MINTS:
        return as_float(first(row, "token_bought_amount", "bought_amount"), 0.0)
    if sold_mint in SOL_MINTS:
        return as_float(first(row, "token_sold_amount", "sold_amount"), 0.0)
    return 0.0


def normalize_row(row: dict[str, str], source_file: str) -> dict[str, Any] | None:
    side, mint, symbol, amount_token = normalize_side_and_token(row)
    if not mint:
        return None
    amount_usd = as_float(first(row, "amount_usd", "usd_amount"), 0.0)
    amount_sol = estimate_sol_amount(row)
    price_usd = as_float(first(row, "price_usd"), 0.0)
    if price_usd <= 0 and amount_usd > 0 and amount_token > 0:
        price_usd = amount_usd / amount_token

    block_time = first(row, "block_time", "block_time_utc", "timestamp")
    block_slot = as_int(first(row, "block_slot", "slot"), 0)
    confidence = "high" if side in {"BUY", "SELL"} and amount_token > 0 else "low"

    return {
        "block_time": block_time,
        "block_time_utc": block_time,
        "block_slot": block_slot,
        "tx_hash": first(row, "tx_id", "tx_hash", "signature"),
        "token_mint": mint,
        "token_symbol": symbol,
        "side": side,
        "trader": first(row, "trader_id", "trader", "wallet", "user"),
        "amount_token": f"{amount_token:.12f}" if amount_token else "",
        "amount_sol": f"{amount_sol:.12f}" if amount_sol else "",
        "amount_usd": f"{amount_usd:.8f}" if amount_usd else "",
        "price_usd": f"{price_usd:.12f}" if price_usd else "",
        "project": first(row, "project", "dex", "platform"),
        "trade_source": first(row, "trade_source", "source"),
        "source_file": source_file,
        "source_schema": "dune_dex_solana_trades_compatible",
        "parse_confidence": confidence,
        "notes": "market-wide imported row; verify multi-hop grouping before final PnL use",
    }


def load_allowed_mints(path: Path | None) -> set[str]:
    if path is None or not path.exists():
        return set()
    rows = read_csv(path)
    mints = {str(row.get("token_mint") or "") for row in rows}
    return {mint for mint in mints if mint}


def build_market_same_token_swaps(input_paths: list[Path], allowed_mints: set[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path in input_paths:
        for row in read_csv(path):
            normalized = normalize_row(row, path.name)
            if not normalized:
                continue
            if allowed_mints and normalized["token_mint"] not in allowed_mints:
                continue
            out.append(normalized)
    out.sort(key=lambda r: (str(r.get("token_mint")), str(r.get("block_time")), as_int(r.get("block_slot"))))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize external market same-token swap exports")
    parser.add_argument("--input", nargs="+", required=True, help="CSV export(s), e.g. Dune dex_solana.trades result")
    parser.add_argument("--entry-context", default=str(DATA_PROCESSED / "entry_context.csv"), help="Optional mint filter source")
    parser.add_argument("--no-mint-filter", action="store_true")
    parser.add_argument("--output", default=str(DATA_PROCESSED / "market_same_token_swaps.csv"))
    args = parser.parse_args()

    ensure_dirs()
    allowed_mints = set() if args.no_mint_filter else load_allowed_mints(Path(args.entry_context))
    rows = build_market_same_token_swaps([Path(p) for p in args.input], allowed_mints)
    write_csv(Path(args.output), rows, FIELDS)
    print(f"[OK] wrote {len(rows)} market same-token swap rows to {args.output}")


if __name__ == "__main__":
    main()

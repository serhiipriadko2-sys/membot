#!/usr/bin/env python3
"""Enrich entry/control context with market-wide same-token swap features.

Inputs:
- data/processed/entry_context.csv
- data/processed/control_points.csv (optional)
- data/processed/market_same_token_swaps.csv

Outputs by default:
- data/processed/entry_context_market.csv
- data/processed/control_points_market.csv

Leakage rule:
Every market feature uses only rows with market block_time strictly before the
anchor time. For control rows the anchor is control_time. For entry rows the
anchor is entry_time.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common import DATA_PROCESSED, as_float, as_int, ensure_dirs, read_csv, write_csv

UNKNOWN = "UNKNOWN"
DEFAULT_WINDOWS = [10, 30, 60, 300]

MARKET_FIELD_TEMPLATES = [
    "market_volume_sol_{w}s",
    "market_volume_usd_{w}s",
    "market_buy_count_{w}s",
    "market_sell_count_{w}s",
    "market_tx_count_{w}s",
    "market_net_buy_sol_{w}s",
    "market_net_buy_usd_{w}s",
    "market_unique_buyers_{w}s",
    "market_unique_sellers_{w}s",
    "market_unique_traders_{w}s",
    "market_largest_buy_usd_{w}s",
    "market_price_return_{w}s",
    "market_price_points_{w}s",
]


def parse_windows(raw: str) -> list[int]:
    windows: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            windows.append(int(part))
    return sorted(set(w for w in windows if w > 0)) or DEFAULT_WINDOWS


def is_known(value: Any) -> bool:
    return value not in (None, "", UNKNOWN)


def parse_time(value: Any) -> int:
    if value in (None, ""):
        return 0
    text = str(value).strip()
    if not text:
        return 0
    if text.replace(".", "", 1).isdigit():
        number = float(text)
        if number > 10_000_000_000:  # milliseconds
            number = number / 1000
        return int(number)
    try:
        normalized = text.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except ValueError:
        return 0


def first(row: dict[str, str], *names: str) -> str:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return str(value)
    return ""


def market_time(row: dict[str, str]) -> int:
    return parse_time(first(row, "block_time", "block_time_utc", "timestamp"))


def side(row: dict[str, str]) -> str:
    return first(row, "side", "swap_side").upper()


def trader(row: dict[str, str]) -> str:
    return first(row, "trader", "trader_id", "wallet", "user")


def market_price(row: dict[str, str]) -> float:
    price = as_float(first(row, "price_usd", "price"), 0.0)
    if price > 0:
        return price
    amount_usd = as_float(first(row, "amount_usd", "usd_amount"), 0.0)
    amount_token = as_float(first(row, "amount_token", "token_amount"), 0.0)
    return amount_usd / amount_token if amount_usd > 0 and amount_token > 0 else 0.0


def build_market_index(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    by_mint: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        mint = first(row, "token_mint", "mint")
        if not mint:
            continue
        row["_parsed_time"] = str(market_time(row))
        by_mint[mint].append(row)
    for mint_rows in by_mint.values():
        mint_rows.sort(key=lambda r: (as_int(r.get("_parsed_time"), 0), as_int(first(r, "block_slot", "slot"), 0), first(r, "tx_hash", "tx_id", "signature")))
    return by_mint


def rows_before_anchor(rows: list[dict[str, str]], anchor_time: int, window: int) -> list[dict[str, str]]:
    start = anchor_time - window
    return [row for row in rows if start <= as_int(row.get("_parsed_time"), 0) < anchor_time]


def stats_for_window(market_rows: list[dict[str, str]], anchor_time: int, window: int) -> dict[str, Any]:
    rows = rows_before_anchor(market_rows, anchor_time, window)
    buys = [row for row in rows if side(row) == "BUY"]
    sells = [row for row in rows if side(row) == "SELL"]
    buy_sol = sum(as_float(first(row, "amount_sol", "sol_amount"), 0.0) for row in buys)
    sell_sol = sum(as_float(first(row, "amount_sol", "sol_amount"), 0.0) for row in sells)
    buy_usd = sum(as_float(first(row, "amount_usd", "usd_amount"), 0.0) for row in buys)
    sell_usd = sum(as_float(first(row, "amount_usd", "usd_amount"), 0.0) for row in sells)
    buyers = {trader(row) for row in buys if trader(row)}
    sellers = {trader(row) for row in sells if trader(row)}
    traders = {trader(row) for row in rows if trader(row)}
    price_points = [market_price(row) for row in rows if market_price(row) > 0]

    price_return: str | float = ""
    if len(price_points) >= 2 and price_points[0] > 0:
        price_return = (price_points[-1] / price_points[0]) - 1.0

    return {
        "market_volume_sol": buy_sol + sell_sol,
        "market_volume_usd": buy_usd + sell_usd,
        "market_buy_count": len(buys),
        "market_sell_count": len(sells),
        "market_tx_count": len(rows),
        "market_net_buy_sol": buy_sol - sell_sol,
        "market_net_buy_usd": buy_usd - sell_usd,
        "market_unique_buyers": len(buyers),
        "market_unique_sellers": len(sellers),
        "market_unique_traders": len(traders),
        "market_largest_buy_usd": max((as_float(first(row, "amount_usd", "usd_amount"), 0.0) for row in buys), default=0.0),
        "market_price_return": price_return,
        "market_price_points": len(price_points),
    }


def anchor_time_for(row: dict[str, str]) -> int:
    return as_int(first(row, "entry_time", "control_time"), 0)


def enrich_rows(context_rows: list[dict[str, str]], market_by_mint: dict[str, list[dict[str, str]]], windows: list[int]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for source in context_rows:
        row: dict[str, Any] = dict(source)
        mint = first(row, "token_mint", "mint")
        anchor_time = anchor_time_for(row)
        market_rows = market_by_mint.get(mint, [])
        total_market_hits = 0
        for window in windows:
            stats = stats_for_window(market_rows, anchor_time, window) if mint and anchor_time else {}
            total_market_hits += int(stats.get("market_tx_count", 0) or 0)
            for key in [template[:-4] if template.endswith("_{w}s") else template for template in []]:
                row[key] = row.get(key, "")
            for metric, value in stats.items():
                out_key = f"{metric}_{window}s"
                row[out_key] = f"{value:.12f}" if isinstance(value, float) else value
            # preserve UNKNOWN for fields not computed because no rows/source
            for template in MARKET_FIELD_TEMPLATES:
                out_key = template.format(w=window)
                if out_key not in row or row[out_key] == "":
                    row[out_key] = UNKNOWN if out_key.startswith("market_") and "price_return" not in out_key else row.get(out_key, "")

        source_note = row.get("feature_source", "")
        if total_market_hits > 0:
            row["market_coverage"] = "market_same_token_swaps"
            row["feature_source"] = ";".join(x for x in [source_note, "market_same_token_swaps"] if x)
            row["context_status"] = "PARTIAL"
            row["context_coverage"] = "wallet_and_market"
            row["notes"] = f"{row.get('notes', '')}; market_same_token_swaps_enriched".strip("; ")
        else:
            row["notes"] = f"{row.get('notes', '')}; no_market_rows_before_anchor".strip("; ")
        enriched.append(row)
    return enriched


def fieldnames_for(rows: list[dict[str, Any]], windows: list[int]) -> list[str]:
    seen: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in seen and not key.startswith("_"):
                seen.append(key)
    for window in windows:
        for template in MARKET_FIELD_TEMPLATES:
            key = template.format(w=window)
            if key not in seen:
                seen.append(key)
    return seen


def enrich_file(input_path: Path, output_path: Path, market_by_mint: dict[str, list[dict[str, str]]], windows: list[int]) -> int:
    if not input_path.exists():
        return 0
    rows = read_csv(input_path)
    enriched = enrich_rows(rows, market_by_mint, windows)
    write_csv(output_path, enriched, fieldnames_for(enriched, windows))
    return len(enriched)


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich entry/control context with market-wide same-token swap features")
    parser.add_argument("--market-swaps", default=str(DATA_PROCESSED / "market_same_token_swaps.csv"))
    parser.add_argument("--entry-context", default=str(DATA_PROCESSED / "entry_context.csv"))
    parser.add_argument("--control-points", default=str(DATA_PROCESSED / "control_points.csv"))
    parser.add_argument("--entry-output", default=str(DATA_PROCESSED / "entry_context_market.csv"))
    parser.add_argument("--control-output", default=str(DATA_PROCESSED / "control_points_market.csv"))
    parser.add_argument("--windows", default="10,30,60,300")
    args = parser.parse_args()

    ensure_dirs()
    windows = parse_windows(args.windows)
    market_rows = read_csv(Path(args.market_swaps))
    market_by_mint = build_market_index(market_rows)
    entry_count = enrich_file(Path(args.entry_context), Path(args.entry_output), market_by_mint, windows)
    control_count = enrich_file(Path(args.control_points), Path(args.control_output), market_by_mint, windows)
    print(f"[OK] enriched entry rows: {entry_count} -> {args.entry_output}")
    print(f"[OK] enriched control rows: {control_count} -> {args.control_output}")
    print(f"[OK] market rows loaded: {len(market_rows)} across {len(market_by_mint)} token mints")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build market-wide pre-entry context from local Dune/DEX trade exports.

This script is RPC-free. It expects a local CSV export such as Dune
`dex_solana.trades` or an equivalent market trade export. Because schemas differ
between exports, the parser accepts multiple common column aliases.

Output rows are anchor-based: every entry or control anchor gets market-wide
features computed strictly before the anchor time.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import DATA_PROCESSED, as_float, as_int, ensure_dirs, read_csv, write_csv

UNKNOWN = "UNKNOWN"
DEFAULT_WINDOWS = [10, 30, 60, 300]
ANCHOR_FIELDS = [
    "anchor_id",
    "anchor_type",
    "entry_signature",
    "token_mint",
    "anchor_time",
    "anchor_slot",
    "source_entry_time",
    "source_entry_slot",
    "market_source",
    "market_coverage",
    "context_status",
    "notes",
]
WINDOW_TEMPLATES = [
    "market_price_change_{w}s",
    "market_price_points_{w}s",
    "market_volume_usd_{w}s",
    "market_volume_sol_{w}s",
    "market_buy_count_{w}s",
    "market_sell_count_{w}s",
    "market_tx_count_{w}s",
    "market_unique_buyers_{w}s",
    "market_unique_sellers_{w}s",
    "market_buy_sell_imbalance_{w}s",
    "market_tx_rate_{w}s",
]


def parse_windows(value: str) -> list[int]:
    out: list[int] = []
    for part in value.split(","):
        part = part.strip()
        if part:
            out.append(int(part))
    return sorted(set(x for x in out if x > 0)) or DEFAULT_WINDOWS


def field(row: dict[str, str], *names: str) -> str:
    for name in names:
        if row.get(name) not in (None, ""):
            return row.get(name, "")
    return ""


def trade_time(row: dict[str, str]) -> int:
    return as_int(field(row, "block_time", "timestamp", "time", "evt_block_time"), 0)


def trade_slot(row: dict[str, str]) -> int:
    return as_int(field(row, "block_slot", "slot", "evt_block_slot"), 0)


def trade_tx(row: dict[str, str]) -> str:
    return field(row, "tx_id", "tx_hash", "signature", "transaction_hash")


def token_mint(row: dict[str, str]) -> str:
    return field(row, "token_mint", "mint", "token_bought_mint_address", "token_sold_mint_address", "token_address")


def trader(row: dict[str, str]) -> str:
    return field(row, "trader_id", "trader", "wallet", "buyer", "seller", "user")


def buyer(row: dict[str, str]) -> str:
    return field(row, "buyer", "token_bought_owner", "trader_id", "trader", "wallet")


def seller(row: dict[str, str]) -> str:
    return field(row, "seller", "token_sold_owner", "trader_id", "trader", "wallet")


def side_for_token(row: dict[str, str], mint: str) -> str:
    side = field(row, "side", "direction").upper()
    if side in {"BUY", "SELL"}:
        return side
    bought = field(row, "token_bought_mint_address", "token_bought_address")
    sold = field(row, "token_sold_mint_address", "token_sold_address")
    if bought == mint:
        return "BUY"
    if sold == mint:
        return "SELL"
    return UNKNOWN


def amount_usd(row: dict[str, str]) -> float:
    return as_float(field(row, "amount_usd", "volume_usd", "usd_amount", "token_pair_amount_usd"), 0.0)


def amount_sol(row: dict[str, str]) -> float:
    value = field(row, "amount_sol", "sol_amount")
    if value:
        return as_float(value, 0.0)
    return 0.0


def price_usd(row: dict[str, str], mint: str) -> float:
    direct = field(row, "price_usd", "token_price_usd")
    if direct:
        return as_float(direct, 0.0)
    bought = field(row, "token_bought_mint_address", "token_bought_address")
    sold = field(row, "token_sold_mint_address", "token_sold_address")
    if bought == mint:
        return as_float(field(row, "token_bought_price", "token_bought_price_usd"), 0.0)
    if sold == mint:
        return as_float(field(row, "token_sold_price", "token_sold_price_usd"), 0.0)
    return 0.0


def fields_for_windows(windows: list[int]) -> list[str]:
    fields = ANCHOR_FIELDS[:]
    for window in windows:
        fields.extend(template.format(w=window) for template in WINDOW_TEMPLATES)
    return fields


def anchors_from_entries(entries: list[dict[str, str]]) -> list[dict[str, str]]:
    anchors: list[dict[str, str]] = []
    for i, row in enumerate(entries, start=1):
        anchors.append({
            "anchor_id": str(i),
            "anchor_type": "entry",
            "entry_signature": field(row, "entry_signature"),
            "token_mint": field(row, "token_mint"),
            "anchor_time": field(row, "entry_time"),
            "anchor_slot": field(row, "entry_slot"),
            "source_entry_time": field(row, "entry_time"),
            "source_entry_slot": field(row, "entry_slot"),
        })
    return anchors


def anchors_from_controls(controls: list[dict[str, str]]) -> list[dict[str, str]]:
    anchors: list[dict[str, str]] = []
    for i, row in enumerate(controls, start=1):
        if not field(row, "control_time"):
            continue
        anchors.append({
            "anchor_id": field(row, "control_id") or str(i),
            "anchor_type": field(row, "control_type") or "control",
            "entry_signature": field(row, "entry_signature"),
            "token_mint": field(row, "token_mint"),
            "anchor_time": field(row, "control_time"),
            "anchor_slot": field(row, "control_slot") or "0",
            "source_entry_time": field(row, "entry_time"),
            "source_entry_slot": field(row, "entry_slot"),
        })
    return anchors


def before_anchor(row: dict[str, str], anchor_time: int, anchor_slot: int, entry_signature: str) -> bool:
    if entry_signature and trade_tx(row) == entry_signature:
        return False
    ts = trade_time(row)
    slot = trade_slot(row)
    if ts <= 0 or anchor_time <= 0:
        return False
    return ts < anchor_time or (ts == anchor_time and slot > 0 and anchor_slot > 0 and slot < anchor_slot)


def window_stats(anchor: dict[str, str], trades_by_mint: dict[str, list[dict[str, str]]], window: int) -> dict[str, Any]:
    mint = field(anchor, "token_mint")
    anchor_time = as_int(field(anchor, "anchor_time"), 0)
    anchor_slot = as_int(field(anchor, "anchor_slot"), 0)
    start = anchor_time - window
    rows = [
        row for row in trades_by_mint.get(mint, [])
        if before_anchor(row, anchor_time, anchor_slot, field(anchor, "entry_signature")) and trade_time(row) >= start
    ]
    if not rows:
        return {
            "price_change": "",
            "price_points": 0,
            "volume_usd": 0.0,
            "volume_sol": 0.0,
            "buy_count": 0,
            "sell_count": 0,
            "tx_count": 0,
            "unique_buyers": 0,
            "unique_sellers": 0,
            "imbalance": "",
            "tx_rate": 0.0,
        }
    prices = [price_usd(row, mint) for row in rows if price_usd(row, mint) > 0]
    price_change = ""
    if len(prices) >= 2 and prices[0] > 0:
        price_change = (prices[-1] / prices[0]) - 1.0
    buys = [row for row in rows if side_for_token(row, mint) == "BUY"]
    sells = [row for row in rows if side_for_token(row, mint) == "SELL"]
    buy_count = len(buys)
    sell_count = len(sells)
    denom = buy_count + sell_count
    imbalance = ((buy_count - sell_count) / denom) if denom else ""
    return {
        "price_change": price_change,
        "price_points": len(prices),
        "volume_usd": sum(amount_usd(row) for row in rows),
        "volume_sol": sum(amount_sol(row) for row in rows),
        "buy_count": buy_count,
        "sell_count": sell_count,
        "tx_count": len(rows),
        "unique_buyers": len({buyer(row) for row in buys if buyer(row)}),
        "unique_sellers": len({seller(row) for row in sells if seller(row)}),
        "imbalance": imbalance,
        "tx_rate": len(rows) / window,
    }


def build_market_context(anchors: list[dict[str, str]], market_trades: list[dict[str, str]], windows: list[int]) -> list[dict[str, Any]]:
    trades_by_mint: dict[str, list[dict[str, str]]] = {}
    for row in market_trades:
        mint = token_mint(row)
        if not mint:
            continue
        trades_by_mint.setdefault(mint, []).append(row)
    for rows in trades_by_mint.values():
        rows.sort(key=lambda row: (trade_time(row), trade_slot(row), trade_tx(row)))
    out: list[dict[str, Any]] = []
    for anchor in anchors:
        row: dict[str, Any] = {name: anchor.get(name, "") for name in ANCHOR_FIELDS}
        row["market_source"] = "local_market_trades_csv"
        observed_any = False
        for window in windows:
            stats = window_stats(anchor, trades_by_mint, window)
            observed_any = observed_any or stats["tx_count"] > 0 or stats["price_points"] > 0
            row[f"market_price_change_{window}s"] = stats["price_change"]
            row[f"market_price_points_{window}s"] = stats["price_points"]
            row[f"market_volume_usd_{window}s"] = stats["volume_usd"]
            row[f"market_volume_sol_{window}s"] = stats["volume_sol"]
            row[f"market_buy_count_{window}s"] = stats["buy_count"]
            row[f"market_sell_count_{window}s"] = stats["sell_count"]
            row[f"market_tx_count_{window}s"] = stats["tx_count"]
            row[f"market_unique_buyers_{window}s"] = stats["unique_buyers"]
            row[f"market_unique_sellers_{window}s"] = stats["unique_sellers"]
            row[f"market_buy_sell_imbalance_{window}s"] = stats["imbalance"]
            row[f"market_tx_rate_{window}s"] = stats["tx_rate"]
        row["market_coverage"] = "market_trades" if observed_any else "none"
        row["context_status"] = "PARTIAL" if observed_any else UNKNOWN
        row["notes"] = "computed strictly before anchor from local market trade export" if observed_any else "no market trades found before anchor"
        out.append(row)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Build market_context.csv from local Dune/DEX trade export")
    parser.add_argument("--entry-context", default=str(DATA_PROCESSED / "entry_context.csv"))
    parser.add_argument("--control-points", default=str(DATA_PROCESSED / "control_points.csv"))
    parser.add_argument("--market-trades", default=str(DATA_PROCESSED / "dune_solana_trades.csv"))
    parser.add_argument("--output", default=str(DATA_PROCESSED / "market_context.csv"))
    parser.add_argument("--include-controls", action="store_true")
    parser.add_argument("--windows", default="10,30,60,300")
    args = parser.parse_args()
    ensure_dirs()
    windows = parse_windows(args.windows)
    anchors = anchors_from_entries(read_csv(Path(args.entry_context)))
    if args.include_controls:
        anchors.extend(anchors_from_controls(read_csv(Path(args.control_points))))
    rows = build_market_context(anchors, read_csv(Path(args.market_trades)), windows)
    write_csv(Path(args.output), rows, fields_for_windows(windows))
    print(f"[OK] wrote {len(rows)} market context rows to {args.output}")


if __name__ == "__main__":
    main()

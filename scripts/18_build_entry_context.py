#!/usr/bin/env python3
"""Build a balanced pre-entry context dataset for BUY prediction study.

The script is deliberately leakage-safe and RPC-free. It reuses existing local
pipeline artifacts only:
- data/processed/wallet_swaps.csv
- data/processed/trades_paired.csv
- data/processed/price_series.csv (optional)

Market-wide context is not fabricated. When only wallet-derived data is
available, market features stay UNKNOWN/empty and `market_coverage` is marked
`wallet_only`.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

from common import DATA_PROCESSED, as_float, as_int, ensure_dirs, read_csv, write_csv

UNKNOWN = "UNKNOWN"
DEFAULT_WINDOWS = [10, 30, 60, 300]

BASE_FIELDS = [
    "sample_id",
    "sample_class",
    "source_trade_index",
    "entry_signature",
    "exit_signature",
    "token_mint",
    "entry_time",
    "entry_time_utc",
    "entry_slot",
    "exit_time",
    "exit_slot",
    "entry_sol",
    "exit_sol",
    "token_amount",
    "label_win",
    "label_pnl_sol",
    "label_hold_seconds",
    "parse_confidence",
    "entry_swap_found",
    "same_wallet_prior_entries_count",
    "same_wallet_prior_pnl_sol",
    "time_since_prev_wallet_buy_seconds",
    "wallet_observed_age_seconds_at_entry",
    "token_age_seconds",
    "ata_created_before_buy",
    "seconds_from_ata_to_buy",
    "market_coverage",
    "context_status",
    "context_coverage",
    "leakage_guard_ok",
    "unknown_fields_count",
    "notes",
]

WINDOW_FIELD_TEMPLATES = [
    "price_return_{w}s",
    "price_points_{w}s",
    "wallet_volume_sol_{w}s",
    "wallet_buy_count_{w}s",
    "wallet_sell_count_{w}s",
    "wallet_net_buy_sol_{w}s",
    "wallet_largest_buy_sol_{w}s",
    "wallet_tx_count_{w}s",
    "market_volume_sol_{w}s",
    "market_buy_count_{w}s",
    "market_sell_count_{w}s",
    "market_unique_buyers_{w}s",
    "market_unique_sellers_{w}s",
]


def fields_for_windows(windows: list[int]) -> list[str]:
    fields = BASE_FIELDS[:]
    insert_at = fields.index("market_coverage")
    window_fields: list[str] = []
    for window in windows:
        for template in WINDOW_FIELD_TEMPLATES:
            window_fields.append(template.format(w=window))
    return fields[:insert_at] + window_fields + fields[insert_at:]


def parse_windows(value: str) -> list[int]:
    windows: list[int] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        seconds = int(part)
        if seconds <= 0:
            raise ValueError("windows must be positive seconds")
        windows.append(seconds)
    return sorted(set(windows)) or DEFAULT_WINDOWS


def is_before_event(row: dict[str, Any], entry_time: int, entry_slot: int, entry_signature: str) -> bool:
    """True only for rows strictly before the entry transaction.

    Same-signature rows are excluded even when timestamps are missing. For equal
    block_time, lower slot is accepted as before; same slot is treated as not
    safely before because intra-slot ordering is not known here.
    """
    if row.get("signature") == entry_signature:
        return False
    row_time = as_int(row.get("block_time", row.get("timestamp")), 0)
    row_slot = as_int(row.get("slot"), 0)
    if row_time <= 0 or entry_time <= 0:
        return False
    if row_time < entry_time:
        return True
    if row_time == entry_time and row_slot > 0 and entry_slot > 0 and row_slot < entry_slot:
        return True
    return False


def to_utc_string(timestamp: int) -> str:
    if timestamp <= 0:
        return ""
    from datetime import datetime, timezone

    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def normalize_trade(trade: dict[str, str], index: int) -> dict[str, Any]:
    pnl = as_float(trade.get("net_pnl_sol"), as_float(trade.get("pnl_sol")))
    return {
        "_source_trade_index": index,
        "token_mint": trade.get("token_mint", ""),
        "entry_signature": trade.get("entry_signature", ""),
        "exit_signature": trade.get("exit_signature", ""),
        "entry_time": as_int(trade.get("entry_time"), 0),
        "exit_time": as_int(trade.get("exit_time"), 0),
        "entry_slot": as_int(trade.get("entry_slot"), 0),
        "exit_slot": as_int(trade.get("exit_slot"), 0),
        "entry_sol": as_float(trade.get("entry_sol"), 0.0),
        "exit_sol": as_float(trade.get("exit_sol"), 0.0),
        "token_amount": as_float(trade.get("token_amount"), 0.0),
        "hold_seconds": as_int(trade.get("hold_seconds"), 0),
        "pnl_sol": pnl,
    }


def select_balanced_trades(
    trades: list[dict[str, str]],
    sample_winners: int,
    sample_losers: int,
) -> list[tuple[str, dict[str, Any]]]:
    normalized = [normalize_trade(trade, idx) for idx, trade in enumerate(trades)]
    normalized = [t for t in normalized if t["token_mint"] and t["entry_signature"] and t["entry_time"]]
    normalized.sort(key=lambda t: (t["entry_time"], t["entry_slot"], t["entry_signature"], t["_source_trade_index"]))
    winners = [t for t in normalized if t["pnl_sol"] > 0]
    losers = [t for t in normalized if t["pnl_sol"] < 0]
    selected: list[tuple[str, dict[str, Any]]] = []
    selected.extend(("winner", trade) for trade in winners[:sample_winners])
    selected.extend(("loser", trade) for trade in losers[:sample_losers])
    selected.sort(key=lambda item: (item[1]["entry_time"], item[1]["entry_slot"], item[1]["_source_trade_index"]))
    return selected


def build_indexes(swaps: list[dict[str, str]], price_series: list[dict[str, str]], trades: list[dict[str, str]]):
    swaps_by_mint: dict[str, list[dict[str, str]]] = defaultdict(list)
    swaps_by_entry: dict[tuple[str, str], dict[str, str]] = {}
    first_wallet_seen_by_mint: dict[str, int] = {}
    for swap in swaps:
        mint = swap.get("token_mint", "")
        if not mint:
            continue
        swaps_by_mint[mint].append(swap)
        sig = swap.get("signature", "")
        if sig:
            swaps_by_entry[(mint, sig)] = swap
        ts = as_int(swap.get("block_time"), 0)
        if ts > 0:
            first_wallet_seen_by_mint[mint] = min(ts, first_wallet_seen_by_mint.get(mint, ts))
    for rows in swaps_by_mint.values():
        rows.sort(key=lambda r: (as_int(r.get("block_time"), 0), as_int(r.get("slot"), 0), r.get("signature", "")))

    prices_by_mint: dict[str, list[dict[str, str]]] = defaultdict(list)
    for point in price_series:
        mint = point.get("token_mint", "")
        if mint:
            prices_by_mint[mint].append(point)
    for rows in prices_by_mint.values():
        rows.sort(key=lambda r: (as_int(r.get("timestamp"), 0), as_int(r.get("slot"), 0), r.get("signature", "")))

    closed_trade_pnl_by_mint: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for idx, trade in enumerate(trades):
        nt = normalize_trade(trade, idx)
        if nt["token_mint"] and nt["exit_time"]:
            closed_trade_pnl_by_mint[nt["token_mint"]].append(nt)
    for rows in closed_trade_pnl_by_mint.values():
        rows.sort(key=lambda r: (r["exit_time"], r["exit_slot"], r["_source_trade_index"]))

    return swaps_by_mint, swaps_by_entry, prices_by_mint, first_wallet_seen_by_mint, closed_trade_pnl_by_mint


def wallet_window_stats(
    swaps_for_mint: list[dict[str, str]],
    entry_time: int,
    entry_slot: int,
    entry_signature: str,
    window: int,
) -> dict[str, Any]:
    start_time = entry_time - window
    prior = [
        row for row in swaps_for_mint
        if is_before_event(row, entry_time, entry_slot, entry_signature)
        and as_int(row.get("block_time"), 0) >= start_time
    ]
    buys = [row for row in prior if row.get("side") == "BUY"]
    sells = [row for row in prior if row.get("side") == "SELL"]
    buy_sol = [as_float(row.get("sol_amount"), 0.0) for row in buys]
    sell_sol = [as_float(row.get("sol_amount"), 0.0) for row in sells]
    return {
        "wallet_volume_sol": sum(buy_sol) + sum(sell_sol),
        "wallet_buy_count": len(buys),
        "wallet_sell_count": len(sells),
        "wallet_net_buy_sol": sum(buy_sol) - sum(sell_sol),
        "wallet_largest_buy_sol": max(buy_sol) if buy_sol else "",
        "wallet_tx_count": len(prior),
    }


def price_return_stats(
    price_points_for_mint: list[dict[str, str]],
    entry_time: int,
    entry_slot: int,
    entry_signature: str,
    window: int,
) -> dict[str, Any]:
    start_time = entry_time - window
    prior = [
        row for row in price_points_for_mint
        if is_before_event(row, entry_time, entry_slot, entry_signature)
        and as_int(row.get("timestamp"), 0) >= start_time
        and as_float(row.get("price_sol"), 0.0) > 0
    ]
    if len(prior) < 2:
        return {"price_return": "", "price_points": len(prior)}
    start_price = as_float(prior[0].get("price_sol"), 0.0)
    end_price = as_float(prior[-1].get("price_sol"), 0.0)
    if start_price <= 0:
        return {"price_return": "", "price_points": len(prior)}
    return {"price_return": (end_price / start_price) - 1.0, "price_points": len(prior)}


def prior_wallet_buy_stats(swaps_for_mint: list[dict[str, str]], entry_time: int, entry_slot: int, entry_signature: str) -> tuple[int, str]:
    prior_buys = [
        row for row in swaps_for_mint
        if row.get("side") == "BUY" and is_before_event(row, entry_time, entry_slot, entry_signature)
    ]
    if not prior_buys:
        return 0, ""
    previous = prior_buys[-1]
    delta = entry_time - as_int(previous.get("block_time"), entry_time)
    return len(prior_buys), str(max(0, delta))


def closed_prior_pnl(closed_trades_for_mint: list[dict[str, Any]], entry_time: int, entry_slot: int) -> float:
    total = 0.0
    for trade in closed_trades_for_mint:
        if trade["exit_time"] < entry_time or (trade["exit_time"] == entry_time and trade["exit_slot"] < entry_slot):
            total += as_float(trade.get("pnl_sol"), 0.0)
    return total


def coverage_status(row: dict[str, Any], windows: list[int]) -> tuple[str, str, int]:
    unknown_market_fields = 0
    wallet_points = 0
    price_points = 0
    for window in windows:
        for name in [
            f"market_volume_sol_{window}s",
            f"market_buy_count_{window}s",
            f"market_sell_count_{window}s",
            f"market_unique_buyers_{window}s",
            f"market_unique_sellers_{window}s",
            "token_age_seconds",
            "ata_created_before_buy",
            "seconds_from_ata_to_buy",
        ]:
            if row.get(name) in ("", UNKNOWN, None):
                unknown_market_fields += 1
        wallet_points += as_int(row.get(f"wallet_tx_count_{window}s"), 0)
        price_points += as_int(row.get(f"price_points_{window}s"), 0)
    if wallet_points == 0 and price_points < 2:
        return UNKNOWN, "none", unknown_market_fields
    if price_points >= 2:
        return "PARTIAL", "wallet_price_and_swaps", unknown_market_fields
    return "PARTIAL", "wallet_swaps_only", unknown_market_fields


def build_entry_context(
    swaps: list[dict[str, str]],
    trades: list[dict[str, str]],
    price_series: list[dict[str, str]],
    sample_winners: int = 30,
    sample_losers: int = 30,
    windows: list[int] | None = None,
) -> list[dict[str, Any]]:
    windows = windows or DEFAULT_WINDOWS
    selected = select_balanced_trades(trades, sample_winners, sample_losers)
    swaps_by_mint, swaps_by_entry, prices_by_mint, first_seen, closed_pnl = build_indexes(swaps, price_series, trades)
    rows: list[dict[str, Any]] = []

    for sample_num, (sample_class, trade) in enumerate(selected, start=1):
        mint = trade["token_mint"]
        entry_signature = trade["entry_signature"]
        entry_time = trade["entry_time"]
        entry_slot = trade["entry_slot"]
        entry_swap = swaps_by_entry.get((mint, entry_signature), {})
        prior_count, seconds_since_prev = prior_wallet_buy_stats(
            swaps_by_mint.get(mint, []), entry_time, entry_slot, entry_signature
        )
        first_mint_seen = first_seen.get(mint, 0)
        wallet_age = entry_time - first_mint_seen if first_mint_seen and entry_time >= first_mint_seen else ""
        row: dict[str, Any] = {
            "sample_id": sample_num,
            "sample_class": sample_class,
            "source_trade_index": trade["_source_trade_index"],
            "entry_signature": entry_signature,
            "exit_signature": trade["exit_signature"],
            "token_mint": mint,
            "entry_time": entry_time,
            "entry_time_utc": to_utc_string(entry_time),
            "entry_slot": entry_slot,
            "exit_time": trade["exit_time"],
            "exit_slot": trade["exit_slot"],
            "entry_sol": trade["entry_sol"],
            "exit_sol": trade["exit_sol"],
            "token_amount": trade["token_amount"],
            "label_win": "true" if trade["pnl_sol"] > 0 else "false",
            "label_pnl_sol": trade["pnl_sol"],
            "label_hold_seconds": trade["hold_seconds"],
            "parse_confidence": entry_swap.get("parse_confidence", ""),
            "entry_swap_found": "true" if entry_swap else "false",
            "same_wallet_prior_entries_count": prior_count,
            "same_wallet_prior_pnl_sol": closed_prior_pnl(closed_pnl.get(mint, []), entry_time, entry_slot),
            "time_since_prev_wallet_buy_seconds": seconds_since_prev,
            "wallet_observed_age_seconds_at_entry": wallet_age,
            "token_age_seconds": UNKNOWN,
            "ata_created_before_buy": UNKNOWN,
            "seconds_from_ata_to_buy": UNKNOWN,
            "market_coverage": "wallet_only",
            "leakage_guard_ok": "true",
            "notes": "market-wide fields require Dune/Helius/getBlock enrichment; no RPC calls made",
        }
        for window in windows:
            price_stats = price_return_stats(prices_by_mint.get(mint, []), entry_time, entry_slot, entry_signature, window)
            wallet_stats = wallet_window_stats(swaps_by_mint.get(mint, []), entry_time, entry_slot, entry_signature, window)
            row[f"price_return_{window}s"] = price_stats["price_return"]
            row[f"price_points_{window}s"] = price_stats["price_points"]
            row[f"wallet_volume_sol_{window}s"] = wallet_stats["wallet_volume_sol"]
            row[f"wallet_buy_count_{window}s"] = wallet_stats["wallet_buy_count"]
            row[f"wallet_sell_count_{window}s"] = wallet_stats["wallet_sell_count"]
            row[f"wallet_net_buy_sol_{window}s"] = wallet_stats["wallet_net_buy_sol"]
            row[f"wallet_largest_buy_sol_{window}s"] = wallet_stats["wallet_largest_buy_sol"]
            row[f"wallet_tx_count_{window}s"] = wallet_stats["wallet_tx_count"]
            row[f"market_volume_sol_{window}s"] = UNKNOWN
            row[f"market_buy_count_{window}s"] = UNKNOWN
            row[f"market_sell_count_{window}s"] = UNKNOWN
            row[f"market_unique_buyers_{window}s"] = UNKNOWN
            row[f"market_unique_sellers_{window}s"] = UNKNOWN
        context_status, context_coverage, unknowns = coverage_status(row, windows)
        row["context_status"] = context_status
        row["context_coverage"] = context_coverage
        row["unknown_fields_count"] = unknowns
        rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a 30 winner / 30 loser pre-entry context dataset")
    parser.add_argument("--swaps", default=str(DATA_PROCESSED / "wallet_swaps.csv"))
    parser.add_argument("--trades", default=str(DATA_PROCESSED / "trades_paired.csv"))
    parser.add_argument("--price-series", default=str(DATA_PROCESSED / "price_series.csv"))
    parser.add_argument("--output", default=str(DATA_PROCESSED / "entry_context.csv"))
    parser.add_argument("--sample-winners", type=int, default=30)
    parser.add_argument("--sample-losers", type=int, default=30)
    parser.add_argument("--windows", default="10,30,60,300")
    args = parser.parse_args()

    ensure_dirs()
    windows = parse_windows(args.windows)
    swaps = read_csv(Path(args.swaps))
    trades = read_csv(Path(args.trades))
    price_series = read_csv(Path(args.price_series))
    rows = build_entry_context(
        swaps=swaps,
        trades=trades,
        price_series=price_series,
        sample_winners=args.sample_winners,
        sample_losers=args.sample_losers,
        windows=windows,
    )
    fieldnames = fields_for_windows(windows)
    write_csv(Path(args.output), rows, fieldnames)
    winners = sum(1 for row in rows if row.get("sample_class") == "winner")
    losers = sum(1 for row in rows if row.get("sample_class") == "loser")
    print(f"[OK] wrote {len(rows)} entry context rows to {args.output} (winners={winners}, losers={losers})")
    if winners < args.sample_winners or losers < args.sample_losers:
        print("[WARN] not enough paired winner/loser trades to satisfy requested balanced sample")


if __name__ == "__main__":
    main()

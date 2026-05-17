#!/usr/bin/env python3
"""Reconcile open positions with FIFO cost basis from normalized trades.

This script does not estimate missing history. If normalized trade history does
not cover current inventory, it reports partial/no FIFO coverage instead of
promoting an estimate to verified accounting.
"""

from __future__ import annotations

import argparse
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from common import DATA_PROCESSED, ensure_dirs, read_csv, write_csv

NEW_FIELDS = [
    "verified_fifo_cost_basis_usd",
    "verified_fifo_unrealized_pnl_usd",
    "verified_fifo_unrealized_pnl_pct",
    "fifo_matched_open_amount",
    "fifo_coverage_pct",
    "fifo_status",
    "cost_basis_status",
    "fifo_notes",
]


def parse_num(value: Any) -> float | None:
    if value in (None, ""):
        return None
    text = str(value).replace(",", "").replace("$", "").strip()
    if text in {"_", "nan", "NaN", "None"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def trade_timestamp_key(row: dict[str, str]) -> str:
    return row.get("timestamp") or row.get("block_time") or ""


def load_trades(path: Path) -> list[dict[str, str]]:
    rows = read_csv(path)
    return sorted(rows, key=trade_timestamp_key)


def build_open_lots_fifo(trades: list[dict[str, str]]) -> dict[str, deque[dict[str, Any]]]:
    lots_by_mint: dict[str, deque[dict[str, Any]]] = defaultdict(deque)
    for row in trades:
        mint = str(row.get("token_mint", "")).strip()
        side = str(row.get("side", "")).lower().strip()
        amount = parse_num(row.get("token_amount")) or 0.0
        usd = parse_num(row.get("usd_amount")) or 0.0
        fee = parse_num(row.get("fee_usd")) or 0.0
        if not mint or amount <= 0:
            continue
        if side == "buy":
            unit_cost = (usd + fee) / amount if amount else 0.0
            lots_by_mint[mint].append({
                "amount": amount,
                "unit_cost_usd": unit_cost,
                "source_tx": row.get("tx_hash") or row.get("signature", ""),
                "timestamp": trade_timestamp_key(row),
            })
        elif side == "sell":
            remaining = amount
            while remaining > 1e-12 and lots_by_mint[mint]:
                lot = lots_by_mint[mint][0]
                take = min(remaining, lot["amount"])
                lot["amount"] -= take
                remaining -= take
                if lot["amount"] <= 1e-12:
                    lots_by_mint[mint].popleft()
    return lots_by_mint


def compute_position_cost(lots: list[dict[str, Any]], current_balance: float | None) -> tuple[float | None, float, float]:
    if current_balance is None or current_balance <= 0:
        return None, 0.0, 0.0
    needed = current_balance
    cost = 0.0
    matched = 0.0
    for lot in lots:
        if needed <= 1e-12:
            break
        take = min(needed, float(lot.get("amount", 0.0)))
        cost += take * float(lot.get("unit_cost_usd", 0.0))
        matched += take
        needed -= take
    coverage = (matched / current_balance * 100.0) if current_balance else 0.0
    return (cost if matched > 0 else None), matched, coverage


def reconcile_positions(positions: list[dict[str, str]], trades: list[dict[str, str]], full_threshold: float = 99.9) -> list[dict[str, Any]]:
    lots_by_mint = build_open_lots_fifo(trades)
    out: list[dict[str, Any]] = []
    for position in positions:
        row: dict[str, Any] = dict(position)
        mint = str(row.get("token_mint", "")).strip()
        balance = parse_num(row.get("balance"))
        current_value = parse_num(row.get("current_value_usd"))
        cost, matched, coverage = compute_position_cost(list(lots_by_mint.get(mint, [])), balance)

        if balance is None or balance <= 0:
            status = "no_position_balance"
            cost_basis_status = "UNKNOWN"
            notes = "No positive current balance to reconcile."
        elif matched <= 0:
            status = "no_fifo_match"
            cost_basis_status = "UNKNOWN"
            notes = "No matching remaining FIFO lots; export window may be incomplete or mint normalization may be wrong."
        elif coverage >= full_threshold:
            status = "verified_fifo_full"
            cost_basis_status = "FIFO_VERIFIED"
            notes = "FIFO cost basis fully covered by normalized trade CSV."
        else:
            status = "partial_fifo_coverage"
            cost_basis_status = "PARTIAL_FIFO"
            notes = "Only part of current balance is covered; extend trade export window or audit mint normalization."

        unrealized = None
        pnl_pct = None
        if current_value is not None and cost is not None:
            unrealized = current_value - cost
            pnl_pct = (unrealized / cost * 100.0) if cost else None

        row["verified_fifo_cost_basis_usd"] = "" if cost is None else round(cost, 8)
        row["verified_fifo_unrealized_pnl_usd"] = "" if unrealized is None else round(unrealized, 8)
        row["verified_fifo_unrealized_pnl_pct"] = "" if pnl_pct is None else round(pnl_pct, 6)
        row["fifo_matched_open_amount"] = round(matched, 8)
        row["fifo_coverage_pct"] = round(coverage, 6)
        row["fifo_status"] = status
        row["cost_basis_status"] = cost_basis_status
        row["fifo_notes"] = notes
        out.append(row)
    return out


def output_fields(positions: list[dict[str, str]]) -> list[str]:
    base: list[str] = []
    for row in positions:
        for key in row.keys():
            if key not in base:
                base.append(key)
    return base + [field for field in NEW_FIELDS if field not in base]


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconcile open positions with FIFO cost basis from normalized trades.")
    parser.add_argument("--positions", default="", help="open_positions.csv path")
    parser.add_argument("--trades", default="", help="trades_normalized.csv path")
    parser.add_argument("--out", default="", help="output CSV path")
    parser.add_argument("--full-threshold", type=float, default=99.9)
    args = parser.parse_args()

    ensure_dirs()
    positions_path = Path(args.positions) if args.positions else DATA_PROCESSED / "open_positions.csv"
    trades_path = Path(args.trades) if args.trades else DATA_PROCESSED / "trades_normalized.csv"
    out_path = Path(args.out) if args.out else DATA_PROCESSED / "open_positions_fifo_verified.csv"

    positions = read_csv(positions_path)
    trades = load_trades(trades_path)
    rows = reconcile_positions(positions, trades, args.full_threshold)
    write_csv(out_path, rows, output_fields(positions))
    print(f"[OK] wrote {len(rows)} reconciled open positions to {out_path}")


if __name__ == "__main__":
    main()

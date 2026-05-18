#!/usr/bin/env python3
"""Build market-wide matched controls from a local Dune/DEX trade export.

Controls are selected from non-entry market activity with the same token and
pre-entry windows. This is a stricter layer than wallet-derived controls because
it can compare the target wallet entry against the broader token market.
"""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path
from typing import Any

from common import DATA_PROCESSED, as_int, ensure_dirs, read_csv, write_csv

market_context = importlib.import_module("25_build_market_context")

FIELDNAMES = [
    "market_control_id",
    "entry_signature",
    "token_mint",
    "entry_time",
    "entry_slot",
    "control_time",
    "control_slot",
    "control_signature",
    "control_type",
    "offset_seconds",
    "matched_by",
    "leakage_guard_ok",
    "notes",
]


def candidate_rows_for_entry(entry: dict[str, str], market_trades: list[dict[str, str]], min_offset: int, max_offset: int) -> list[dict[str, str]]:
    mint = entry.get("token_mint", "")
    entry_time = as_int(entry.get("entry_time"), 0)
    entry_slot = as_int(entry.get("entry_slot"), 0)
    entry_sig = entry.get("entry_signature", "")
    out = []
    for row in market_trades:
        if market_context.token_mint(row) != mint:
            continue
        if market_context.trade_tx(row) == entry_sig:
            continue
        ts = market_context.trade_time(row)
        slot = market_context.trade_slot(row)
        if ts <= 0:
            continue
        offset = ts - entry_time
        if not (-max_offset <= offset <= -min_offset):
            continue
        if not market_context.before_anchor(row, entry_time, entry_slot, entry_sig):
            continue
        out.append(row)
    out.sort(key=lambda row: (abs(market_context.trade_time(row) - entry_time), market_context.trade_time(row), market_context.trade_slot(row)))
    return out


def build_market_controls(
    entries: list[dict[str, str]],
    market_trades: list[dict[str, str]],
    controls_per_entry: int = 5,
    min_offset_seconds: int = 60,
    max_offset_seconds: int = 1800,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    control_id = 0
    for entry in entries:
        candidates = candidate_rows_for_entry(entry, market_trades, min_offset_seconds, max_offset_seconds)
        for candidate in candidates[:controls_per_entry]:
            control_id += 1
            control_time = market_context.trade_time(candidate)
            entry_time = as_int(entry.get("entry_time"), 0)
            rows.append({
                "market_control_id": control_id,
                "entry_signature": entry.get("entry_signature", ""),
                "token_mint": entry.get("token_mint", ""),
                "entry_time": entry.get("entry_time", ""),
                "entry_slot": entry.get("entry_slot", ""),
                "control_time": control_time,
                "control_slot": market_context.trade_slot(candidate),
                "control_signature": market_context.trade_tx(candidate),
                "control_type": "same_token_market_pre_entry",
                "offset_seconds": control_time - entry_time,
                "matched_by": "same_token;pre_entry;nearest_time",
                "leakage_guard_ok": "true",
                "notes": "selected from local market trade export; no future data used",
            })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Build market-wide pre-entry controls")
    parser.add_argument("--entry-context", default=str(DATA_PROCESSED / "entry_context.csv"))
    parser.add_argument("--market-trades", default=str(DATA_PROCESSED / "dune_solana_trades.csv"))
    parser.add_argument("--output", default=str(DATA_PROCESSED / "market_control_points.csv"))
    parser.add_argument("--controls-per-entry", type=int, default=5)
    parser.add_argument("--min-offset-seconds", type=int, default=60)
    parser.add_argument("--max-offset-seconds", type=int, default=1800)
    args = parser.parse_args()
    ensure_dirs()
    rows = build_market_controls(
        read_csv(Path(args.entry_context)),
        read_csv(Path(args.market_trades)),
        args.controls_per_entry,
        args.min_offset_seconds,
        args.max_offset_seconds,
    )
    write_csv(Path(args.output), rows, FIELDNAMES)
    print(f"[OK] wrote {len(rows)} market controls to {args.output}")


if __name__ == "__main__":
    main()

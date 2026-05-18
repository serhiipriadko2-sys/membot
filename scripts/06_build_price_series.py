#!/usr/bin/env python3
"""Build a first-pass price series from normalized wallet swap rows.

This is not a market-wide price oracle. It is a wallet-derived replay aid.
Use it for guarded H3 experiments and mark results as UNKNOWN when coverage is thin.
"""

from __future__ import annotations

import argparse
from typing import Any

from common import DATA_PROCESSED, ensure_dirs, read_csv, write_csv

FIELDS = ["token_mint", "timestamp", "slot", "price_sol", "signature", "source", "coverage_note"]


def build_price_series(swaps: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for swap in swaps:
        price = swap.get("price_sol")
        if swap.get("side") not in {"BUY", "SELL"}:
            continue
        if price in (None, ""):
            continue
        rows.append({
            "token_mint": swap.get("token_mint", ""),
            "timestamp": swap.get("block_time", ""),
            "slot": swap.get("slot", ""),
            "price_sol": price,
            "signature": swap.get("signature", ""),
            "source": "wallet_swap_price",
            "coverage_note": "wallet-derived-only",
        })
    rows.sort(key=lambda r: (r.get("token_mint", ""), int(float(r.get("timestamp") or 0)), int(float(r.get("slot") or 0))))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a first-pass price series from normalized swaps")
    parser.add_argument("--input", default=str(DATA_PROCESSED / "wallet_swaps.csv"))
    parser.add_argument("--output", default=str(DATA_PROCESSED / "price_series.csv"))
    args = parser.parse_args()

    ensure_dirs()
    swaps = read_csv(__import__("pathlib").Path(args.input))
    rows = build_price_series(swaps)
    write_csv(__import__("pathlib").Path(args.output), rows, FIELDS)
    print(f"[OK] wrote {len(rows)} price points")


if __name__ == "__main__":
    main()

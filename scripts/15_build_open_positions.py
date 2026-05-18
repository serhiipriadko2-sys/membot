#!/usr/bin/env python3
"""Build open_positions.csv from unpaired buy inventory in wallet_swaps.csv."""

from __future__ import annotations
from collections import defaultdict
from pathlib import Path
from common import DATA_PROCESSED, as_float, as_int, ensure_dirs, read_csv, write_csv

FIELDS = [
    "token_mint", "side", "balance", "cost_basis_sol",
    "avg_entry_price_sol", "first_buy_time", "last_buy_time",
    "buy_count", "sell_count", "net_sol_flow", "status",
]


def build_open_positions(swaps: list[dict[str, str]]) -> list[dict[str, object]]:
    mints: dict[str, dict[str, object]] = defaultdict(lambda: {
        "buy_sol": 0.0, "sell_sol": 0.0, "buy_tokens": 0.0, "sell_tokens": 0.0,
        "buy_count": 0, "sell_count": 0, "first_buy": 0, "last_buy": 0,
    })

    for row in swaps:
        mint = row.get("token_mint", "")
        side = str(row.get("side", "")).upper()
        if not mint or side not in ("BUY", "SELL"):
            continue
        sol = as_float(row.get("sol_amount"), 0.0)
        tokens = as_float(row.get("token_amount"), 0.0)
        ts = as_int(row.get("block_time"), 0)
        m = mints[mint]
        if side == "BUY":
            m["buy_sol"] += sol
            m["buy_tokens"] += tokens
            m["buy_count"] += 1
            if ts > 0:
                if m["first_buy"] == 0 or ts < m["first_buy"]:
                    m["first_buy"] = ts
                if ts > m["last_buy"]:
                    m["last_buy"] = ts
        else:
            m["sell_sol"] += sol
            m["sell_tokens"] += tokens
            m["sell_count"] += 1

    rows = []
    for mint, m in sorted(mints.items()):
        net_tokens = m["buy_tokens"] - m["sell_tokens"]
        net_sol = m["buy_sol"] - m["sell_sol"]
        if net_tokens > 0.01:  # still holds tokens
            rows.append({
                "token_mint": mint,
                "side": "LONG",
                "balance": round(net_tokens, 6),
                "cost_basis_sol": round(net_sol, 6),
                "avg_entry_price_sol": round(m["buy_sol"] / m["buy_tokens"], 12) if m["buy_tokens"] else 0,
                "first_buy_time": m["first_buy"],
                "last_buy_time": m["last_buy"],
                "buy_count": m["buy_count"],
                "sell_count": m["sell_count"],
                "net_sol_flow": round(net_sol, 6),
                "status": "open",
            })

    return sorted(rows, key=lambda r: -abs(r["cost_basis_sol"]))


def main():
    ensure_dirs()
    swaps = read_csv(DATA_PROCESSED / "wallet_swaps.csv")
    rows = build_open_positions(swaps)
    write_csv(DATA_PROCESSED / "open_positions.csv", rows, FIELDS)
    print(f"[OK] wrote {len(rows)} open positions to {DATA_PROCESSED / 'open_positions.csv'}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Pair normalized BUY/SELL swaps using FIFO lots."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from common import DATA_PROCESSED, as_float, as_int, ensure_dirs, read_csv, write_csv

FIELDS = [
    "token_mint",
    "entry_signature",
    "exit_signature",
    "entry_time",
    "exit_time",
    "entry_slot",
    "exit_slot",
    "hold_seconds",
    "entry_sol",
    "exit_sol",
    "token_amount",
    "pnl_sol",
    "fees_sol",
    "net_pnl_sol",
    "pairing_method",
    "pairing_confidence",
]


def _ts(value: Any) -> int:
    return as_int(value, 0)


def pair_fifo(swaps: list[dict[str, str]]) -> list[dict[str, Any]]:
    lots: dict[str, deque[dict[str, Any]]] = defaultdict(deque)
    trades: list[dict[str, Any]] = []
    sorted_swaps = sorted(swaps, key=lambda r: (_ts(r.get("block_time")), as_int(r.get("slot"))))

    for row in sorted_swaps:
        mint = row.get("token_mint", "")
        side = row.get("side", "")
        token_amount = as_float(row.get("token_amount"))
        sol_amount = as_float(row.get("sol_amount"))
        if not mint or token_amount <= 0 or sol_amount <= 0:
            continue
        if side == "BUY":
            lots[mint].append(
                {
                    "remaining_tokens": token_amount,
                    "remaining_cost": sol_amount,
                    "entry_signature": row.get("signature", ""),
                    "entry_time": _ts(row.get("block_time")),
                    "entry_slot": as_int(row.get("slot")),
                }
            )
        elif side == "SELL":
            remaining_sell_tokens = token_amount
            while remaining_sell_tokens > 0 and lots[mint]:
                lot = lots[mint][0]
                used_tokens = min(remaining_sell_tokens, lot["remaining_tokens"])
                fraction_of_sell = used_tokens / token_amount if token_amount else 0
                proceeds = sol_amount * fraction_of_sell
                fraction_of_lot = used_tokens / lot["remaining_tokens"] if lot["remaining_tokens"] else 0
                cost = lot["remaining_cost"] * fraction_of_lot
                pnl = proceeds - cost
                exit_time = _ts(row.get("block_time"))
                entry_time = lot["entry_time"]
                trades.append(
                    {
                        "token_mint": mint,
                        "entry_signature": lot["entry_signature"],
                        "exit_signature": row.get("signature", ""),
                        "entry_time": entry_time,
                        "exit_time": exit_time,
                        "entry_slot": lot["entry_slot"],
                        "exit_slot": as_int(row.get("slot")),
                        "hold_seconds": max(0, exit_time - entry_time),
                        "entry_sol": cost,
                        "exit_sol": proceeds,
                        "token_amount": used_tokens,
                        "pnl_sol": pnl,
                        "fees_sol": "",
                        "net_pnl_sol": pnl,
                        "pairing_method": "fifo",
                        "pairing_confidence": "medium",
                    }
                )
                lot["remaining_tokens"] -= used_tokens
                lot["remaining_cost"] -= cost
                remaining_sell_tokens -= used_tokens
                if lot["remaining_tokens"] <= 1e-12:
                    lots[mint].popleft()
    return trades


def main() -> None:
    ensure_dirs()
    swaps = read_csv(DATA_PROCESSED / "wallet_swaps.csv")
    trades = pair_fifo(swaps)
    write_csv(DATA_PROCESSED / "trades_paired.csv", trades, FIELDS)
    print(f"[OK] wrote {len(trades)} paired trades")


if __name__ == "__main__":
    main()

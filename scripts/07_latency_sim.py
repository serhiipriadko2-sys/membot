#!/usr/bin/env python3
"""Latency sensitivity simulation with explicit invalid/unknown states.

Rules:
- Time delays use timestamp progression.
- Slot delays use slot progression, never +1 second.
- Delayed entries at or after exit are invalid_after_exit.
- Missing delayed prices produce no_price, not fake PnL.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from common import DATA_PROCESSED, as_float, as_int, ensure_dirs, read_csv, write_csv

TIME_DELAYS = {"3s": 3, "10s": 10, "30s": 30}
SLOT_DELAYS = {"1slot": 1, "3slots": 3}

BASE_FIELDS = [
    "token_mint", "entry_signature", "exit_signature", "real_pnl_sol",
    "entry_time", "exit_time", "entry_slot", "exit_slot", "token_amount",
]
FIELDS = BASE_FIELDS + [
    "status_3s", "sim_pnl_3s", "delayed_price_3s", "invalid_reason_3s",
    "status_10s", "sim_pnl_10s", "delayed_price_10s", "invalid_reason_10s",
    "status_30s", "sim_pnl_30s", "delayed_price_30s", "invalid_reason_30s",
    "status_1slot", "sim_pnl_1slot", "delayed_price_1slot", "invalid_reason_1slot",
    "status_3slots", "sim_pnl_3slots", "delayed_price_3slots", "invalid_reason_3slots",
]


@dataclass(frozen=True)
class PricePoint:
    token_mint: str
    timestamp: int
    slot: int
    price_sol: float


def load_price_points(rows: list[dict[str, str]]) -> list[PricePoint]:
    points = []
    for row in rows:
        price = as_float(row.get("price_sol"), -1)
        if price <= 0:
            continue
        points.append(
            PricePoint(
                token_mint=row.get("token_mint", ""),
                timestamp=as_int(row.get("timestamp")),
                slot=as_int(row.get("slot")),
                price_sol=price,
            )
        )
    return sorted(points, key=lambda p: (p.token_mint, p.timestamp, p.slot))


def find_price_by_time(points: list[PricePoint], token_mint: str, target_timestamp: int, exit_time: int) -> PricePoint | None:
    candidates = [p for p in points if p.token_mint == token_mint and p.timestamp >= target_timestamp and p.timestamp < exit_time]
    return min(candidates, key=lambda p: (p.timestamp, p.slot), default=None)


def find_price_by_slot(points: list[PricePoint], token_mint: str, target_slot: int, exit_slot: int) -> PricePoint | None:
    candidates = [p for p in points if p.token_mint == token_mint and p.slot >= target_slot and p.slot < exit_slot]
    return min(candidates, key=lambda p: (p.slot, p.timestamp), default=None)


def simulate_one(trade: dict[str, str], points: list[PricePoint]) -> dict[str, Any]:
    token_mint = trade.get("token_mint", "")
    entry_time = as_int(trade.get("entry_time"))
    exit_time = as_int(trade.get("exit_time"))
    entry_slot = as_int(trade.get("entry_slot"))
    exit_slot = as_int(trade.get("exit_slot"))
    token_amount = as_float(trade.get("token_amount"))
    exit_sol = as_float(trade.get("exit_sol"))
    real_pnl = as_float(trade.get("net_pnl_sol"), as_float(trade.get("pnl_sol")))

    out: dict[str, Any] = {
        "token_mint": token_mint,
        "entry_signature": trade.get("entry_signature", ""),
        "exit_signature": trade.get("exit_signature", ""),
        "real_pnl_sol": real_pnl,
        "entry_time": entry_time,
        "exit_time": exit_time,
        "entry_slot": entry_slot,
        "exit_slot": exit_slot,
        "token_amount": token_amount,
    }

    for label, delay in TIME_DELAYS.items():
        target = entry_time + delay
        if target >= exit_time:
            out[f"status_{label}"] = "invalid_after_exit"
            out[f"invalid_reason_{label}"] = "delayed_timestamp_gte_exit_time"
            out[f"sim_pnl_{label}"] = ""
            out[f"delayed_price_{label}"] = ""
            continue
        point = find_price_by_time(points, token_mint, target, exit_time)
        if point is None:
            out[f"status_{label}"] = "no_price"
            out[f"invalid_reason_{label}"] = "no_price_before_exit"
            out[f"sim_pnl_{label}"] = ""
            out[f"delayed_price_{label}"] = ""
            continue
        delayed_cost = point.price_sol * token_amount
        out[f"status_{label}"] = "valid"
        out[f"invalid_reason_{label}"] = ""
        out[f"delayed_price_{label}"] = point.price_sol
        out[f"sim_pnl_{label}"] = exit_sol - delayed_cost

    for label, delay in SLOT_DELAYS.items():
        target = entry_slot + delay
        if target >= exit_slot:
            out[f"status_{label}"] = "invalid_after_exit"
            out[f"invalid_reason_{label}"] = "delayed_slot_gte_exit_slot"
            out[f"sim_pnl_{label}"] = ""
            out[f"delayed_price_{label}"] = ""
            continue
        point = find_price_by_slot(points, token_mint, target, exit_slot)
        if point is None:
            out[f"status_{label}"] = "no_price"
            out[f"invalid_reason_{label}"] = "no_price_before_exit_slot"
            out[f"sim_pnl_{label}"] = ""
            out[f"delayed_price_{label}"] = ""
            continue
        delayed_cost = point.price_sol * token_amount
        out[f"status_{label}"] = "valid"
        out[f"invalid_reason_{label}"] = ""
        out[f"delayed_price_{label}"] = point.price_sol
        out[f"sim_pnl_{label}"] = exit_sol - delayed_cost

    return out


def simulate_latency(trades: list[dict[str, str]], price_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    points = load_price_points(price_rows)
    return [simulate_one(trade, points) for trade in trades]


def main() -> None:
    ensure_dirs()
    trades = read_csv(DATA_PROCESSED / "trades_paired.csv")
    price_rows = read_csv(DATA_PROCESSED / "price_series.csv")
    rows = simulate_latency(trades, price_rows)
    write_csv(DATA_PROCESSED / "latency_sim.csv", rows, FIELDS)
    print(f"[OK] wrote {len(rows)} latency rows")


if __name__ == "__main__":
    main()

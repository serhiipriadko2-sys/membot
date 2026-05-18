#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import DATA_PROCESSED, as_float, ensure_dirs, read_csv, write_csv

SCENARIOS = [
    {"scenario": "ideal_0s", "delay_sec": 0, "buy_slippage_pct": 0.0, "sell_slippage_pct": 0.0},
    {"scenario": "fast_bot_1s", "delay_sec": 1, "buy_slippage_pct": 0.005, "sell_slippage_pct": 0.005},
    {"scenario": "normal_copy_5s", "delay_sec": 5, "buy_slippage_pct": 0.01, "sell_slippage_pct": 0.01},
    {"scenario": "late_copy_15s", "delay_sec": 15, "buy_slippage_pct": 0.02, "sell_slippage_pct": 0.02},
    {"scenario": "retail_lag_30s", "delay_sec": 30, "buy_slippage_pct": 0.05, "sell_slippage_pct": 0.05},
    {"scenario": "manual_60s", "delay_sec": 60, "buy_slippage_pct": 0.10, "sell_slippage_pct": 0.10},
]

FIELDS = ["scenario","delay_sec","token_mint","entry_signature","exit_signature","original_net_pnl_usd","copy_cost_usd","copy_proceeds_usd","gmgn_fee_usd","extra_fee_usd","copy_net_pnl_usd","copy_pnl_delta_usd","stress_model_not_latency_replay"]

def stress_rows(rows: list[dict[str, str]], gmgn_fee_pct: float = 0.01, extra_fee_usd_per_trade: float = 0.05) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        entry_usd = as_float(row.get("entry_usd"))
        exit_usd = as_float(row.get("exit_usd"))
        original_net = as_float(row.get("net_pnl_usd"), exit_usd - entry_usd)
        for scenario in SCENARIOS:
            copy_cost = entry_usd * (1 + scenario["buy_slippage_pct"])
            copy_proceeds = exit_usd * (1 - scenario["sell_slippage_pct"])
            gmgn_fee = (copy_cost + copy_proceeds) * gmgn_fee_pct
            extra_fee = 2 * extra_fee_usd_per_trade
            copy_net = copy_proceeds - copy_cost - gmgn_fee - extra_fee
            out.append({
                "scenario": scenario["scenario"],
                "delay_sec": scenario["delay_sec"],
                "token_mint": row.get("token_mint", ""),
                "entry_signature": row.get("entry_signature", ""),
                "exit_signature": row.get("exit_signature", ""),
                "original_net_pnl_usd": original_net,
                "copy_cost_usd": copy_cost,
                "copy_proceeds_usd": copy_proceeds,
                "gmgn_fee_usd": gmgn_fee,
                "extra_fee_usd": extra_fee,
                "copy_net_pnl_usd": copy_net,
                "copy_pnl_delta_usd": copy_net - original_net,
                "stress_model_not_latency_replay": "true",
            })
    return out

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--gmgn-fee-pct", type=float, default=0.01)
    parser.add_argument("--extra-fee-usd-per-trade", type=float, default=0.05)
    args = parser.parse_args()
    ensure_dirs()
    input_path = Path(args.input) if args.input else DATA_PROCESSED / "fee_adjusted_pnl.csv"
    output_path = Path(args.output) if args.output else DATA_PROCESSED / "copy_stress_model.csv"
    rows = stress_rows(read_csv(input_path), args.gmgn_fee_pct, args.extra_fee_usd_per_trade)
    write_csv(output_path, rows, FIELDS)
    print(f"[OK] wrote {len(rows)} copy-stress rows to {output_path}")

if __name__ == "__main__":
    main()

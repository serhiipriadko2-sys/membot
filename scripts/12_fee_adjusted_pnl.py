#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import DATA_PROCESSED, as_float, ensure_dirs, read_csv, write_csv

FIELDS = ["token_mint","entry_signature","exit_signature","entry_time","exit_time","entry_usd","exit_usd","gross_pnl_usd","observed_fee_usd","fee_confidence","net_pnl_usd","hold_seconds","pairing_method","pairing_confidence"]

def _first(row: dict[str, str], keys: list[str]) -> str:
    for key in keys:
        if row.get(key) not in (None, ""):
            return str(row[key])
    return ""

def calculate(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        entry_usd = as_float(_first(row, ["entry_usd", "matched_cost_usd"]))
        exit_usd = as_float(_first(row, ["exit_usd", "sell_proceeds_usd"]))
        if not entry_usd and row.get("entry_sol"):
            entry_usd = as_float(row.get("entry_sol"))
        if not exit_usd and row.get("exit_sol"):
            exit_usd = as_float(row.get("exit_sol"))
        gross = exit_usd - entry_usd
        fee_raw = _first(row, ["observed_fee_usd", "fee_usd", "fees_usd"])
        fee = as_float(fee_raw, 0.0)
        fee_confidence = "high" if fee_raw not in (None, "") else "low_missing_observed_fee"
        out.append({
            "token_mint": row.get("token_mint", ""),
            "entry_signature": row.get("entry_signature", row.get("buy_tx", "")),
            "exit_signature": row.get("exit_signature", row.get("sell_tx", "")),
            "entry_time": row.get("entry_time", row.get("buy_time", "")),
            "exit_time": row.get("exit_time", row.get("sell_time", "")),
            "entry_usd": entry_usd,
            "exit_usd": exit_usd,
            "gross_pnl_usd": gross,
            "observed_fee_usd": fee,
            "fee_confidence": fee_confidence,
            "net_pnl_usd": gross - fee,
            "hold_seconds": row.get("hold_seconds", ""),
            "pairing_method": row.get("pairing_method", "fifo"),
            "pairing_confidence": row.get("pairing_confidence", "medium"),
        })
    return out

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="")
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    ensure_dirs()
    input_path = Path(args.input) if args.input else DATA_PROCESSED / "trades_paired.csv"
    output_path = Path(args.output) if args.output else DATA_PROCESSED / "fee_adjusted_pnl.csv"
    rows = calculate(read_csv(input_path))
    write_csv(output_path, rows, FIELDS)
    print(f"[OK] wrote {len(rows)} fee-adjusted rows to {output_path}")

if __name__ == "__main__":
    main()

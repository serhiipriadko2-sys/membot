#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import DATA_PROCESSED, ensure_dirs, read_csv, write_csv

FIELDS = ["wallet","signature","block_time","slot","token_mint","token_symbol","side","token_amount","usd_amount","sol_amount","price_usd","market_cap_at_trade","dex","fee_usd","fee_sol","source","parse_confidence"]

ALIASES = {
    "signature": ["signature", "tx_hash", "tx_id", "hash"],
    "block_time": ["block_time", "timestamp", "time"],
    "wallet": ["wallet", "owner", "address"],
    "side": ["side", "type", "action"],
    "token_mint": ["token_mint", "mint", "token_address"],
    "token_symbol": ["token_symbol", "symbol"],
    "token_amount": ["token_amount", "amount"],
    "usd_amount": ["usd_amount", "amount_usd"],
    "sol_amount": ["sol_amount", "amount_sol"],
    "parse_confidence": ["parse_confidence", "confidence"],
}

def pick(row: dict[str, str], field: str) -> str:
    for key in ALIASES.get(field, [field]):
        if row.get(key) not in (None, ""):
            return str(row[key]).strip()
    return ""

def normalize_side(value: str) -> str:
    value = value.strip().upper()
    if value in {"BUY", "BOUGHT", "PURCHASE"}:
        return "BUY"
    if value in {"SELL", "SOLD", "SALE"}:
        return "SELL"
    return ""

def normalize_row(row: dict[str, str], skip_unknown_side: bool = True) -> dict[str, Any] | None:
    side = normalize_side(pick(row, "side"))
    confidence = pick(row, "parse_confidence") or "medium"
    if not side:
        if skip_unknown_side:
            return None
        side = "UNKNOWN"
        confidence = "low"
    out = {field: pick(row, field) for field in FIELDS}
    out["side"] = side
    out["parse_confidence"] = confidence
    out["source"] = out.get("source") or "csv_import"
    return out

def import_rows(input_csv: Path, skip_unknown_side: bool = True) -> list[dict[str, Any]]:
    return [r for r in (normalize_row(row, skip_unknown_side) for row in read_csv(input_csv)) if r is not None]

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="")
    parser.add_argument("--keep-unknown-side", action="store_true")
    args = parser.parse_args()
    ensure_dirs()
    rows = import_rows(Path(args.input), skip_unknown_side=not args.keep_unknown_side)
    output = Path(args.output) if args.output else DATA_PROCESSED / "wallet_swaps.csv"
    write_csv(output, rows, FIELDS)
    print(f"[OK] wrote {len(rows)} normalized swaps to {output}")

if __name__ == "__main__":
    main()

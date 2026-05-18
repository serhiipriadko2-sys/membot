#!/usr/bin/env python3
"""Build Helius-style enrichment rows from a local enhanced transactions export.

No API calls are made here. Keep Helius keys out of the repository. Export JSON
externally, place it under data/raw or data/processed, and use this parser to
normalize fee/tip/token-transfer context.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from common import DATA_PROCESSED, ensure_dirs, write_csv

FIELDNAMES = [
    "signature",
    "timestamp",
    "slot",
    "fee_lamports",
    "native_transfer_count",
    "token_transfer_count",
    "account_data_count",
    "token_balance_change_count",
    "source",
    "parse_status",
    "notes",
]


def load_json(path: Path) -> Any:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def tx_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("transactions", "result", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [payload]
    return []


def count_token_balance_changes(tx: dict[str, Any]) -> int:
    account_data = tx.get("accountData") or tx.get("account_data") or []
    total = 0
    if isinstance(account_data, list):
        for item in account_data:
            if isinstance(item, dict):
                changes = item.get("tokenBalanceChanges") or item.get("token_balance_changes") or []
                if isinstance(changes, list):
                    total += len(changes)
    return total


def build_helius_enrichment(payload: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for tx in tx_items(payload):
        native = tx.get("nativeTransfers") or tx.get("native_transfers") or []
        token = tx.get("tokenTransfers") or tx.get("token_transfers") or []
        account_data = tx.get("accountData") or tx.get("account_data") or []
        rows.append({
            "signature": tx.get("signature", ""),
            "timestamp": tx.get("timestamp") or tx.get("blockTime") or "",
            "slot": tx.get("slot", ""),
            "fee_lamports": tx.get("fee", ""),
            "native_transfer_count": len(native) if isinstance(native, list) else "",
            "token_transfer_count": len(token) if isinstance(token, list) else "",
            "account_data_count": len(account_data) if isinstance(account_data, list) else "",
            "token_balance_change_count": count_token_balance_changes(tx),
            "source": "helius_enhanced_export",
            "parse_status": "PARTIAL",
            "notes": "parsed from local export; no API call made; verify Helius product status in source audit",
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize a local Helius enhanced transactions JSON export")
    parser.add_argument("--input", default=str(DATA_PROCESSED / "helius_enhanced_transactions.json"))
    parser.add_argument("--output", default=str(DATA_PROCESSED / "helius_enrichment.csv"))
    args = parser.parse_args()
    ensure_dirs()
    rows = build_helius_enrichment(load_json(Path(args.input)))
    write_csv(Path(args.output), rows, FIELDNAMES)
    print(f"[OK] wrote {len(rows)} Helius enrichment rows to {args.output}")


if __name__ == "__main__":
    main()

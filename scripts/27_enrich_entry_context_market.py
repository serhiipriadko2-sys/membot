#!/usr/bin/env python3
"""Join market-wide context features onto entry_context.csv.

The script does not compute market features itself. It joins rows produced by
`25_build_market_context.py` and preserves UNKNOWN where coverage is missing.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import DATA_PROCESSED, ensure_dirs, read_csv, write_csv

UNKNOWN = "UNKNOWN"


def key_for_entry(row: dict[str, str]) -> tuple[str, str, str]:
    return (row.get("entry_signature", ""), row.get("token_mint", ""), row.get("entry_time", ""))


def key_for_market(row: dict[str, str]) -> tuple[str, str, str]:
    return (row.get("entry_signature", ""), row.get("token_mint", ""), row.get("anchor_time", ""))


def market_fields(rows: list[dict[str, str]]) -> list[str]:
    fields: list[str] = []
    for row in rows:
        for name in row:
            if name.startswith("market_") and name not in fields:
                fields.append(name)
    return fields


def enrich_entry_context(entry_rows: list[dict[str, str]], market_rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[str]]:
    lookup = {key_for_market(row): row for row in market_rows if row.get("anchor_type") == "entry"}
    fields = market_fields(market_rows)
    output: list[dict[str, Any]] = []
    for entry in entry_rows:
        row: dict[str, Any] = dict(entry)
        market = lookup.get(key_for_entry(entry), {})
        for field in fields:
            row[field] = market.get(field, row.get(field, ""))
        row["market_enriched"] = "true" if market else "false"
        row["market_context_status"] = market.get("context_status", UNKNOWN if not market else "")
        output.append(row)
    base_fields = list(entry_rows[0].keys()) if entry_rows else []
    for field in fields + ["market_enriched", "market_context_status"]:
        if field not in base_fields:
            base_fields.append(field)
    return output, base_fields


def main() -> None:
    parser = argparse.ArgumentParser(description="Join market_context.csv onto entry_context.csv")
    parser.add_argument("--entry-context", default=str(DATA_PROCESSED / "entry_context.csv"))
    parser.add_argument("--market-context", default=str(DATA_PROCESSED / "market_context.csv"))
    parser.add_argument("--output", default=str(DATA_PROCESSED / "entry_context_market_enriched.csv"))
    args = parser.parse_args()
    ensure_dirs()
    rows, fields = enrich_entry_context(read_csv(Path(args.entry_context)), read_csv(Path(args.market_context)))
    write_csv(Path(args.output), rows, fields)
    print(f"[OK] wrote {len(rows)} market-enriched entry rows to {args.output}")


if __name__ == "__main__":
    main()

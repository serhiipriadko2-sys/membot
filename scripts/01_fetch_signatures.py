#!/usr/bin/env python3
"""Fetch wallet signatures from Solana RPC and store them as raw evidence."""

from __future__ import annotations

import argparse
from typing import Any

from common import DATA_RAW, TARGET_WALLET, COMMITMENT, ensure_dirs, polite_sleep, read_json, rpc_call, utc_now_iso, write_json


def fetch_signatures(wallet: str, limit: int, before: str | None = None, until: str | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cursor = before
    while len(rows) < limit:
        batch_limit = min(1000, limit - len(rows))
        options: dict[str, Any] = {"limit": batch_limit, "commitment": COMMITMENT}
        if cursor:
            options["before"] = cursor
        if until:
            options["until"] = until
        batch = rpc_call("getSignaturesForAddress", [wallet, options]) or []
        if not batch:
            break
        rows.extend(batch)
        cursor = batch[-1].get("signature")
        polite_sleep()
        if len(batch) < batch_limit:
            break
    return rows[:limit]


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch raw wallet signatures")
    parser.add_argument("--wallet", default=TARGET_WALLET)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--before", default=None)
    parser.add_argument("--until", default=None)
    parser.add_argument("--output", default=str(DATA_RAW / "signatures_raw.json"))
    args = parser.parse_args()

    ensure_dirs()
    rows = fetch_signatures(args.wallet, args.limit, before=args.before, until=args.until)
    payload = {
        "wallet": args.wallet,
        "limit_requested": args.limit,
        "count": len(rows),
        "fetched_at": utc_now_iso(),
        "items": rows,
    }
    write_json(DATA_RAW / "signatures_raw.json" if args.output == str(DATA_RAW / "signatures_raw.json") else __import__("pathlib").Path(args.output), payload)
    print(f"[OK] wrote {len(rows)} signatures")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Fetch full transactions for previously fetched signatures."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import DATA_RAW, COMMITMENT, ensure_dirs, polite_sleep, read_json, rpc_call, utc_now_iso, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch full transactions from raw signatures")
    parser.add_argument("--input", default=str(DATA_RAW / "signatures_raw.json"))
    parser.add_argument("--output", default=str(DATA_RAW / "transactions_raw.json"))
    args = parser.parse_args()

    ensure_dirs()
    signature_payload = read_json(Path(args.input), default={"items": []})
    signatures = signature_payload.get("items", [])
    rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for item in signatures:
        signature = item.get("signature") if isinstance(item, dict) else str(item)
        if not signature:
            continue
        try:
            result = rpc_call(
                "getTransaction",
                [
                    signature,
                    {
                        "commitment": COMMITMENT,
                        "encoding": "jsonParsed",
                        "maxSupportedTransactionVersion": 0,
                    },
                ],
            )
            rows.append({"signature": signature, "result": result, "signature_meta": item})
        except Exception as exc:
            errors.append({"signature": signature, "error": repr(exc)})
        polite_sleep()

    payload = {
        "wallet": signature_payload.get("wallet"),
        "signatures_count": len(signatures),
        "count": len(rows),
        "error_count": len(errors),
        "fetched_at": utc_now_iso(),
        "items": rows,
        "errors": errors,
    }
    write_json(Path(args.output), payload)
    print(f"[OK] wrote {len(rows)} transactions; errors={len(errors)}")


if __name__ == "__main__":
    main()

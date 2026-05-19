#!/usr/bin/env python3
"""Fetch full transactions for previously fetched signatures.

The script is resumable by default: existing successful rows in the output are
kept, and only missing signatures are fetched. Failed signatures are retried in
later runs unless `--no-resume` is used.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import DATA_RAW, COMMITMENT, ensure_dirs, polite_sleep, read_json, rpc_call, utc_now_iso, write_json


def existing_successes(path: Path) -> dict[str, dict[str, Any]]:
    payload = read_json(path, default={"items": []})
    rows: dict[str, dict[str, Any]] = {}
    for row in payload.get("items", []) or []:
        if not isinstance(row, dict):
            continue
        signature = row.get("signature")
        if signature:
            rows[str(signature)] = row
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch full transactions from raw signatures")
    parser.add_argument("--input", default=str(DATA_RAW / "signatures_raw.json"))
    parser.add_argument("--output", default=str(DATA_RAW / "transactions_raw.json"))
    parser.add_argument("--no-resume", action="store_true", help="Ignore existing output and refetch all signatures")
    parser.add_argument("--max-errors", type=int, default=0, help="Stop after N errors; 0 means do not stop early")
    args = parser.parse_args()

    ensure_dirs()
    input_path = Path(args.input)
    output_path = Path(args.output)
    signature_payload = read_json(input_path, default={"items": []})
    signatures = signature_payload.get("items", [])

    existing = {} if args.no_resume else existing_successes(output_path)
    rows_by_signature: dict[str, dict[str, Any]] = dict(existing)
    errors: list[dict[str, Any]] = []
    skipped = 0

    for item in signatures:
        signature = item.get("signature") if isinstance(item, dict) else str(item)
        if not signature:
            continue
        if signature in rows_by_signature:
            skipped += 1
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
            rows_by_signature[signature] = {"signature": signature, "result": result, "signature_meta": item}
        except Exception as exc:
            errors.append({"signature": signature, "error": repr(exc)})
            if args.max_errors and len(errors) >= args.max_errors:
                print(f"[WARN] stopping after max-errors={args.max_errors}")
                break
        polite_sleep()

    rows = list(rows_by_signature.values())
    payload = {
        "wallet": signature_payload.get("wallet"),
        "signatures_count": len(signatures),
        "count": len(rows),
        "error_count": len(errors),
        "skipped_existing": skipped,
        "coverage_pct": round((len(rows) / len(signatures) * 100), 4) if signatures else 0,
        "fetched_at": utc_now_iso(),
        "items": rows,
        "errors": errors,
    }
    write_json(output_path, payload)
    print(
        f"[OK] wrote {len(rows)} transactions; "
        f"errors={len(errors)} skipped_existing={skipped} coverage={payload['coverage_pct']}%"
    )


if __name__ == "__main__":
    main()

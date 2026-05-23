#!/usr/bin/env python3
"""Smoke-only detector emitter for Observer latency CSV plumbing.

This file exists to validate the no-key observer delivery path. It does not
connect to Solana, Jupiter, Helius, wallets, signing flows, swap endpoints, or
private-key material. Real network measurement is performed by
`scripts/fast10_observer.py`; this helper only emits deterministic smoke rows.
"""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

from observer_gate_eval import REQUIRED_FIELDS


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "observer_latency_live.csv"


def build_smoke_row(
    index: int,
    *,
    base_ts_ms: int,
    detector_latency_ms: float,
    quote_latency_ms: float,
) -> dict[str, str]:
    signal_ts_ms = float(base_ts_ms + index * 1_000)
    detected_ts_ms = signal_ts_ms + detector_latency_ms
    quote_start_ts_ms = detected_ts_ms
    quote_end_ts_ms = quote_start_ts_ms + quote_latency_ms
    total_latency_ms = quote_end_ts_ms - signal_ts_ms
    return {
        "signal_ts_ms": str(signal_ts_ms).rstrip("0").rstrip("."),
        "detected_ts_ms": str(detected_ts_ms).rstrip("0").rstrip("."),
        "quote_start_ts_ms": str(quote_start_ts_ms).rstrip("0").rstrip("."),
        "quote_end_ts_ms": str(quote_end_ts_ms).rstrip("0").rstrip("."),
        "detector_latency_ms": str(float(detector_latency_ms)),
        "quote_latency_ms": str(float(quote_latency_ms)),
        "total_latency_ms": str(float(total_latency_ms)),
        "quote_ok": "true",
        "error": "",
    }


def write_smoke_latency_csv(
    output: Path,
    *,
    rows: int = 1,
    base_ts_ms: int | None = None,
    detector_latency_ms: float = 95.0,
    quote_latency_ms: float = 250.0,
) -> None:
    if rows < 1:
        raise ValueError("rows must be >= 1")
    base = base_ts_ms if base_ts_ms is not None else int(time.time() * 1000)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REQUIRED_FIELDS)
        writer.writeheader()
        for index in range(rows):
            writer.writerow(
                build_smoke_row(
                    index,
                    base_ts_ms=base,
                    detector_latency_ms=detector_latency_ms,
                    quote_latency_ms=quote_latency_ms,
                )
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Emit smoke-only observer_latency_live.csv rows")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Path to observer_latency_live.csv")
    parser.add_argument("--rows", type=int, default=1, help="Smoke rows to write")
    parser.add_argument("--detector-latency-ms", type=float, default=95.0)
    parser.add_argument("--quote-latency-ms", type=float, default=250.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = Path(args.output)
    write_smoke_latency_csv(
        output,
        rows=args.rows,
        detector_latency_ms=args.detector_latency_ms,
        quote_latency_ms=args.quote_latency_ms,
    )
    print(f"SMOKE_ONLY wrote {args.rows} row(s) to {output}")
    print("Observer harness validated; live network run pending.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

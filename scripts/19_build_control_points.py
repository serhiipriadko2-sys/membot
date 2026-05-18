#!/usr/bin/env python3
"""Build matched wallet-derived control points for entry trigger tests.

Controls are generated without RPC calls from `entry_context.csv`,
`wallet_swaps.csv`, and `price_series.csv`.

This is intentionally conservative:
- same-token before-entry controls only by default
- optional after-entry controls are labeled separately
- no market-wide context is fabricated
"""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path
from typing import Any

from common import DATA_PROCESSED, ensure_dirs, read_csv, write_csv

entry_context = importlib.import_module("18_build_entry_context")
UNKNOWN = entry_context.UNKNOWN

CONTROL_BASE_FIELDS = [
    "control_id",
    "entry_sample_id",
    "control_type",
    "control_time",
    "control_time_utc",
    "control_slot",
    "entry_signature",
    "token_mint",
    "entry_time",
    "entry_slot",
    "offset_seconds",
    "feature_family",
    "feature_source",
    "feature_coverage_pct",
    "confidence",
    "market_coverage",
    "context_status",
    "context_coverage",
    "leakage_guard_ok",
    "unknown_fields_count",
    "notes",
]


def fields_for_windows(windows: list[int]) -> list[str]:
    fields = CONTROL_BASE_FIELDS[:]
    insert_at = fields.index("feature_family")
    window_fields: list[str] = []
    for window in windows:
        for template in entry_context.WINDOW_FIELD_TEMPLATES:
            window_fields.append(template.format(w=window))
    return fields[:insert_at] + window_fields + fields[insert_at:]


def parse_offsets(value: str) -> list[int]:
    offsets: list[int] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        offsets.append(int(part))
    if not offsets:
        raise ValueError("at least one control offset is required")
    return sorted(set(offsets))


def build_control_points(
    entries: list[dict[str, str]],
    swaps: list[dict[str, str]],
    price_series: list[dict[str, str]],
    windows: list[int] | None = None,
    offsets: list[int] | None = None,
    include_after: bool = False,
) -> list[dict[str, Any]]:
    windows = windows or entry_context.DEFAULT_WINDOWS
    offsets = offsets or [-300, -120, -60]
    swaps_by_mint, _swaps_by_entry, prices_by_mint, _first_seen, _closed_pnl = entry_context.build_indexes(swaps, price_series, [])
    rows: list[dict[str, Any]] = []
    control_id = 0

    for entry in entries:
        mint = entry.get("token_mint", "")
        entry_time = entry_context.as_int(entry.get("entry_time"), 0)
        entry_slot = entry_context.as_int(entry.get("entry_slot"), 0)
        entry_sig = entry.get("entry_signature", "")
        sample_id = entry.get("sample_id", "")
        if not mint or entry_time <= 0:
            continue
        for offset in offsets:
            if offset >= 0 and not include_after:
                continue
            control_time = entry_time + offset
            if control_time <= 0:
                continue
            control_id += 1
            row: dict[str, Any] = {
                "control_id": control_id,
                "entry_sample_id": sample_id,
                "control_type": "same_token_pre_entry" if offset < 0 else "same_token_post_entry",
                "control_time": control_time,
                "control_time_utc": entry_context.to_utc_string(control_time),
                "control_slot": "",
                "entry_signature": entry_sig,
                "token_mint": mint,
                "entry_time": entry_time,
                "entry_slot": entry_slot,
                "offset_seconds": offset,
                "leakage_guard_ok": "true" if offset < 0 else "false",
                "notes": "wallet-derived control; market-wide fields remain UNKNOWN",
                "token_age_seconds": UNKNOWN,
                "ata_created_before_buy": UNKNOWN,
                "seconds_from_ata_to_buy": UNKNOWN,
            }
            entry_context.apply_window_features(
                row=row,
                mint=mint,
                anchor_time=control_time,
                anchor_slot=0,
                excluded_signature="",
                swaps_by_mint=swaps_by_mint,
                prices_by_mint=prices_by_mint,
                windows=windows,
            )
            entry_context.finalize_feature_metadata(row, windows)
            rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Build matched wallet-derived control points")
    parser.add_argument("--entry-context", default=str(DATA_PROCESSED / "entry_context.csv"))
    parser.add_argument("--swaps", default=str(DATA_PROCESSED / "wallet_swaps.csv"))
    parser.add_argument("--price-series", default=str(DATA_PROCESSED / "price_series.csv"))
    parser.add_argument("--output", default=str(DATA_PROCESSED / "control_points.csv"))
    parser.add_argument("--windows", default="10,30,60,300")
    parser.add_argument("--offsets", default="-300,-120,-60")
    parser.add_argument("--include-after", action="store_true")
    args = parser.parse_args()

    ensure_dirs()
    windows = entry_context.parse_windows(args.windows)
    offsets = parse_offsets(args.offsets)
    rows = build_control_points(
        entries=read_csv(Path(args.entry_context)),
        swaps=read_csv(Path(args.swaps)),
        price_series=read_csv(Path(args.price_series)),
        windows=windows,
        offsets=offsets,
        include_after=args.include_after,
    )
    write_csv(Path(args.output), rows, fields_for_windows(windows))
    print(f"[OK] wrote {len(rows)} control points to {args.output}")


if __name__ == "__main__":
    main()

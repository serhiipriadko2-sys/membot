#!/usr/bin/env python3
"""Verify that a forensic artifact ZIP can power Iskra Forge widgets.

This script does not validate trading truth. It checks whether the artifact contains
CSV files and columns needed by the four live UI widgets:
- token interaction cluster map
- Daily PnL calendar heatmap
- Fee/Jito orbit
- trigger radar / signal cards

Usage:
    python scripts/verify_forge_artifact_widgets.py forensic-verification-123.zip
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import zipfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

import pandas as pd

REQUIRED_FILES = {
    "wallet_swaps": "data/processed/wallet_swaps.csv",
    "daily_pnl_calendar": "data/processed/daily_pnl_calendar.csv",
    "priority_fee_jito_audit": "data/processed/priority_fee_jito_audit.csv",
    "trigger_tests": "data/processed/trigger_tests.csv",
}

FALLBACK_FILES = {
    "trigger_tests": "data/processed/entry_exit_hypothesis_tests.csv",
    "wallet_swaps": "data/processed/trades_paired.csv",
}

COLUMN_SETS = {
    "cluster_token": ["token_mint", "mint", "base_mint", "token_address", "token", "symbol"],
    "cluster_side": ["side", "swap_side", "action", "type"],
    "cluster_amount": ["sol_amount", "amount_sol", "amount_in", "amount_out", "usd_value", "value", "net_pnl_sol", "pnl_sol"],
    "calendar_date": ["date_utc", "date", "day", "bucket_date"],
    "calendar_pnl": ["net_pnl_sol", "pnl_sol", "gross_pnl_sol", "net_pnl_usd", "pnl_usd"],
    "fee_verdict": ["verdict", "fee_verdict", "evidence_verdict"],
    "fee_jito": ["has_jito_tip", "jito_tip", "jito_detected"],
    "fee_compute_budget": ["has_compute_budget_ix", "compute_budget", "has_priority_fee"],
    "trigger_name": ["trigger", "hypothesis", "feature", "name", "family", "scope"],
    "trigger_status": ["status", "verdict", "result"],
    "trigger_score": ["score", "confidence", "support", "lift", "precision", "win_rate", "value"],
    "trigger_note": ["evidence", "notes", "summary", "description", "reason"],
}


@dataclass
class FileCheck:
    widget: str
    file_name: str | None
    exists: bool
    rows: int
    columns: int
    required_columns_found: dict[str, str | None]
    status: str
    reason: str


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def find_member(names: Iterable[str], primary: str, fallback: str | None = None) -> str | None:
    existing = set(names)
    if primary in existing:
        return primary
    if fallback and fallback in existing:
        return fallback
    suffix_primary = "/" + primary
    suffix_fallback = "/" + fallback if fallback else None
    for name in existing:
        if name.endswith(suffix_primary) or (suffix_fallback and name.endswith(suffix_fallback)):
            return name
    return None


def read_csv_from_zip(zf: zipfile.ZipFile, member: str) -> pd.DataFrame:
    with zf.open(member) as f:
        raw = f.read()
    return pd.read_csv(io.BytesIO(raw))


def find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    return next((col for col in candidates if col in df.columns), None)


def check_widget(
    zf: zipfile.ZipFile,
    names: list[str],
    widget: str,
    file_key: str,
    column_keys: list[str],
    min_required: list[str],
) -> FileCheck:
    member = find_member(names, REQUIRED_FILES[file_key], FALLBACK_FILES.get(file_key))
    if not member:
        return FileCheck(widget, None, False, 0, 0, {}, "UNKNOWN", f"Missing {REQUIRED_FILES[file_key]}")
    try:
        df = read_csv_from_zip(zf, member)
    except Exception as exc:
        return FileCheck(widget, member, True, 0, 0, {}, "FAIL", f"CSV read error: {exc}")
    found = {key: find_col(df, COLUMN_SETS[key]) for key in column_keys}
    missing_required = [key for key in min_required if not found.get(key)]
    if df.empty:
        status = "UNKNOWN"
        reason = "CSV exists but has zero rows"
    elif missing_required:
        status = "PARTIAL"
        reason = "Missing required columns: " + ", ".join(missing_required)
    else:
        status = "PASS"
        reason = "Widget can render from this artifact"
    return FileCheck(widget, member, True, int(len(df)), int(len(df.columns)), found, status, reason)


def verify(zip_path: Path) -> dict[str, object]:
    if not zip_path.exists():
        raise FileNotFoundError(zip_path)
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        checks = [
            check_widget(zf, names, "cluster_map", "wallet_swaps", ["cluster_token", "cluster_side", "cluster_amount"], ["cluster_token"]),
            check_widget(zf, names, "daily_pnl_calendar", "daily_pnl_calendar", ["calendar_date", "calendar_pnl"], ["calendar_date", "calendar_pnl"]),
            check_widget(zf, names, "fee_jito_orbit", "priority_fee_jito_audit", ["fee_verdict", "fee_jito", "fee_compute_budget"], ["fee_verdict"]),
            check_widget(zf, names, "signal_cards_and_radar", "trigger_tests", ["trigger_name", "trigger_status", "trigger_score", "trigger_note"], ["trigger_name"]),
        ]
    verdict = "PASS" if all(c.status == "PASS" for c in checks) else "PARTIAL" if any(c.status == "PASS" for c in checks) else "UNKNOWN"
    return {
        "artifact": str(zip_path),
        "bytes": zip_path.stat().st_size,
        "sha256": sha256(zip_path),
        "verdict": verdict,
        "checks": [asdict(c) for c in checks],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Iskra Forge widget readiness from artifact ZIP")
    parser.add_argument("zip_path", type=Path)
    parser.add_argument("--json", dest="json_path", type=Path, default=None)
    args = parser.parse_args()
    result = verify(args.zip_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.json_path:
        args.json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if result["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

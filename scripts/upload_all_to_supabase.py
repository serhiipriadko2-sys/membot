#!/usr/bin/env python3
"""Upload pipeline CSV artifacts to Supabase dataset tables.

Credentials are read from environment variables only. Never commit service role
or secret keys to the repository.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"

load_dotenv(ROOT / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SECRET_KEY") or ""
WALLET = os.getenv("TARGET_WALLET", "7BNaxx6KdUYrjACNQZ9He26NBFoFxujQMAfNLnArLGH5")

ARTIFACTS = {
    "wallet_swaps": DATA / "wallet_swaps.csv",
    "trades_paired": DATA / "trades_paired.csv",
    "latency_sim": DATA / "latency_sim.csv",
    "fee_adjusted_pnl": DATA / "fee_adjusted_pnl.csv",
    "copy_stress_model": DATA / "copy_stress_model.csv",
    "entry_context": DATA / "entry_context.csv",
    "control_points": DATA / "control_points.csv",
    "trigger_tests": DATA / "trigger_tests.csv",
    "open_positions": DATA / "open_positions.csv",
}


def _headers() -> dict[str, str]:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL is required")
    if not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY or SUPABASE_SECRET_KEY is required")
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def upload() -> None:
    headers = _headers()

    run_payload = {
        "wallet": WALLET,
        "label": "full-pipeline-9-artifacts",
        "source": "local_pipeline",
        "status": "completed",
        "stats": {"artifact_count": len(ARTIFACTS)},
        "notes": "All 9 pipeline artifacts: swaps, trades, latency, fees, copy-stress, entry, controls, triggers, positions",
    }

    response = requests.post(f"{SUPABASE_URL}/rest/v1/dataset_runs", headers=headers, json=run_payload, timeout=15)
    response.raise_for_status()
    run = response.json()
    run_id = run[0]["id"] if isinstance(run, list) else run["id"]
    print(f"[OK] Created run: {run_id}")

    total_rows = 0
    uploaded = 0
    for artifact_type, path in ARTIFACTS.items():
        if not path.exists():
            print(f"[SKIP] {artifact_type}: {path.name} not found")
            continue

        content = path.read_text(encoding="utf-8")
        row_count = max(0, content.count("\n") - 1)
        sha = hashlib.sha256(content.encode()).hexdigest()

        payload = {
            "run_id": run_id,
            "artifact_type": artifact_type,
            "file_name": path.name,
            "content_format": "csv",
            "row_count": row_count,
            "sha256": sha,
            "content_text": content,
            "metadata": {"uploaded_via": "upload_all_to_supabase.py"},
        }

        artifact_response = requests.post(
            f"{SUPABASE_URL}/rest/v1/dataset_artifacts",
            headers=headers,
            json=payload,
            timeout=60,
        )
        artifact_response.raise_for_status()
        total_rows += row_count
        uploaded += 1
        print(f"[OK] {artifact_type}: {row_count} rows, {len(content):,} bytes")

    print(f"\nDone! Run ID: {run_id}")
    print(f"Total: {uploaded}/{len(ARTIFACTS)} artifacts, {total_rows:,} rows")


if __name__ == "__main__":
    upload()

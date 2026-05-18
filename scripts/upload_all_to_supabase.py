#!/usr/bin/env python3
"""Upload ALL pipeline CSV artifacts to Supabase dataset tables."""

import hashlib
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"

SUPABASE_URL = "https://catntmobfcenkhkodnqv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNhdG50bW9iZmNlbmtoa29kbnF2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3OTA3NjY0OCwiZXhwIjoyMDk0NjUyNjQ4fQ.CNs93M6NfmoFwOzf6i0KyrLAwOJtjzY8I9ENkqBesZI"
WALLET = "7BNaxx6KdUYrjACNQZ9He26NBFoFxujQMAfNLnArLGH5"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

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


def upload():
    # 1. Create run
    run_payload = {
        "wallet": WALLET,
        "label": "full-pipeline-9-artifacts",
        "source": "local_pipeline",
        "status": "completed",
        "stats": {"artifact_count": len(ARTIFACTS)},
        "notes": "All 9 pipeline artifacts: swaps, trades, latency, fees, copy-stress, entry, controls, triggers, positions",
    }

    r = requests.post(f"{SUPABASE_URL}/rest/v1/dataset_runs", headers=HEADERS, json=run_payload, timeout=15)
    r.raise_for_status()
    run = r.json()
    run_id = run[0]["id"] if isinstance(run, list) else run["id"]
    print(f"[OK] Created run: {run_id}")

    # 2. Upload artifacts
    total_rows = 0
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

        r2 = requests.post(f"{SUPABASE_URL}/rest/v1/dataset_artifacts", headers=HEADERS, json=payload, timeout=60)
        r2.raise_for_status()
        total_rows += row_count
        print(f"[OK] {artifact_type}: {row_count} rows, {len(content):,} bytes")

    print(f"\nDone! Run ID: {run_id}")
    print(f"Total: {len(ARTIFACTS)} artifacts, {total_rows:,} rows")


if __name__ == "__main__":
    upload()

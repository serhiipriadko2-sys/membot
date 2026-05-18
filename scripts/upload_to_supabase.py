#!/usr/bin/env python3
"""Upload local pipeline CSV artifacts to Supabase dataset tables."""

import hashlib
import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]

# Supabase config — read from .streamlit/secrets.toml or env
SUPABASE_URL = "https://catntmobfcenkhkodnqv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNhdG50bW9iZmNlbmtoa29kbnF2Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3OTA3NjY0OCwiZXhwIjoyMDk0NjUyNjQ4fQ.CNs93M6NfmoFwOzf6i0KyrLAwOJtjzY8I9ENkqBesZI"
WALLET = os.getenv("TARGET_WALLET", "7BNaxx6KdUYrjACNQZ9He26NBFoFxujQMAfNLnArLGH5")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

ARTIFACTS = {
    "wallet_swaps": ROOT / "data" / "processed" / "wallet_swaps.csv",
    "trades_paired": ROOT / "data" / "processed" / "trades_paired.csv",
}


def upload():
    # 1. Create run
    run_payload = {
        "wallet": WALLET,
        "label": "pipeline-600tx-fresh",
        "source": "local_pipeline",
        "status": "completed",
        "stats": {
            "signatures": 600,
            "transactions": 599,
            "swaps": 599,
            "paired_trades": 250,
        },
        "notes": "Fresh 600-tx pipeline run via forensic_deep_analysis.py",
    }

    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/dataset_runs",
        headers=HEADERS,
        json=run_payload,
        timeout=15,
    )
    r.raise_for_status()
    run = r.json()
    run_id = run[0]["id"] if isinstance(run, list) else run["id"]
    print(f"[OK] Created run: {run_id}")

    # 2. Upload artifacts
    for artifact_type, path in ARTIFACTS.items():
        if not path.exists():
            print(f"[SKIP] {artifact_type}: file not found at {path}")
            continue

        content = path.read_text(encoding="utf-8")
        row_count = content.count("\n") - 1  # minus header
        sha = hashlib.sha256(content.encode()).hexdigest()

        artifact_payload = {
            "run_id": run_id,
            "artifact_type": artifact_type,
            "file_name": path.name,
            "content_format": "csv",
            "row_count": row_count,
            "sha256": sha,
            "content_text": content,
            "metadata": {"uploaded_via": "upload_to_supabase.py"},
        }

        r2 = requests.post(
            f"{SUPABASE_URL}/rest/v1/dataset_artifacts",
            headers=HEADERS,
            json=artifact_payload,
            timeout=30,
        )
        r2.raise_for_status()
        print(f"[OK] Uploaded {artifact_type}: {row_count} rows, {len(content)} bytes, sha={sha[:16]}...")

    print(f"\nDone! Run ID: {run_id}")
    print("Switch Streamlit sidebar to 'Supabase' and select this run.")


if __name__ == "__main__":
    upload()

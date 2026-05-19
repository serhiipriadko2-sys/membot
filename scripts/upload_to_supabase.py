#!/usr/bin/env python3
"""Upload local pipeline artifacts to Supabase dataset tables.

Security rules:
- Never hardcode Supabase credentials in this file.
- Read SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY/SUPABASE_SECRET_KEY from env or .env.
- Rotate any previously committed service_role key before using this script again.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WALLET = "7BNaxx6KdUYrjACNQZ9He26NBFoFxujQMAfNLnArLGH5"

ARTIFACTS = {
    "wallet_swaps": ROOT / "data" / "processed" / "wallet_swaps.csv",
    "trades_paired": ROOT / "data" / "processed" / "trades_paired.csv",
    "daily_pnl_calendar": ROOT / "data" / "processed" / "daily_pnl_calendar.csv",
    "priority_fee_jito_audit": ROOT / "data" / "processed" / "priority_fee_jito_audit.csv",
    "daily_pnl_calendar_report": ROOT / "reports" / "daily_pnl_calendar_report.md",
    "priority_fee_jito_audit_report": ROOT / "reports" / "priority_fee_jito_audit_report.md",
    "entry_exit_hypothesis_tests": ROOT / "data" / "processed" / "entry_exit_hypothesis_tests.csv",
    "entry_exit_hypothesis_report": ROOT / "reports" / "entry_exit_hypothesis_report.md",
}


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def supabase_key() -> str:
    return (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        or os.getenv("SUPABASE_SECRET_KEY", "").strip()
        or os.getenv("SUPABASE_KEY", "").strip()
    )


def row_count_for(path: Path, content: str) -> int:
    if path.suffix.lower() != ".csv":
        return 0
    try:
        reader = csv.reader(content.splitlines())
        rows = list(reader)
    except Exception:
        return max(content.count("\n") - 1, 0)
    if not rows:
        return 0
    return max(len(rows) - 1, 0)


def content_format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return "csv"
    if suffix in {".md", ".markdown"}:
        return "markdown"
    if suffix == ".json":
        return "json"
    return "text"


def existing_artifacts() -> dict[str, dict[str, Any]]:
    artifacts: dict[str, dict[str, Any]] = {}
    for artifact_type, path in ARTIFACTS.items():
        if not path.exists():
            print(f"[SKIP] {artifact_type}: file not found at {path}")
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        data = content.encode("utf-8")
        artifacts[artifact_type] = {
            "artifact_type": artifact_type,
            "path": path,
            "file_name": path.name,
            "content_format": content_format(path),
            "row_count": row_count_for(path, content),
            "sha256": hashlib.sha256(data).hexdigest(),
            "content_text": content,
            "bytes": len(data),
        }
    return artifacts


def upload() -> None:
    supabase_url = require_env("SUPABASE_URL").rstrip("/")
    key = supabase_key()
    if not key:
        raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY, SUPABASE_SECRET_KEY, or SUPABASE_KEY")

    wallet = os.getenv("TARGET_WALLET", DEFAULT_WALLET)
    label = os.getenv("DATASET_RUN_LABEL", "forensic-verification-upload")
    notes = os.getenv("DATASET_RUN_NOTES", "Uploaded by scripts/upload_to_supabase.py")
    artifacts = existing_artifacts()
    if not artifacts:
        raise RuntimeError("No artifacts found to upload")

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    run_payload = {
        "wallet": wallet,
        "label": label,
        "source": "local_pipeline",
        "status": "completed",
        "stats": {
            "artifact_count": len(artifacts),
            "row_count_total": sum(int(a.get("row_count") or 0) for a in artifacts.values()),
            "artifact_types": sorted(artifacts.keys()),
        },
        "notes": notes,
    }

    response = requests.post(
        f"{supabase_url}/rest/v1/dataset_runs",
        headers=headers,
        json=run_payload,
        timeout=15,
    )
    response.raise_for_status()
    run = response.json()
    run_id = run[0]["id"] if isinstance(run, list) else run["id"]
    print(f"[OK] Created run: {run_id}")

    for artifact_type, artifact in artifacts.items():
        payload = {
            "run_id": run_id,
            "artifact_type": artifact_type,
            "file_name": artifact["file_name"],
            "content_format": artifact["content_format"],
            "row_count": artifact["row_count"],
            "sha256": artifact["sha256"],
            "content_text": artifact["content_text"],
            "metadata": {
                "uploaded_via": "upload_to_supabase.py",
                "bytes": artifact["bytes"],
                "path": str(Path(artifact["path"]).relative_to(ROOT)),
            },
        }
        artifact_response = requests.post(
            f"{supabase_url}/rest/v1/dataset_artifacts",
            headers=headers,
            json=payload,
            timeout=30,
        )
        artifact_response.raise_for_status()
        print(
            f"[OK] Uploaded {artifact_type}: "
            f"{artifact['row_count']} rows, {artifact['bytes']} bytes, sha={artifact['sha256'][:16]}..."
        )

    print(f"\nDone! Run ID: {run_id}")
    print("Switch Streamlit sidebar to 'Supabase' and select this run.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload local forensic artifacts to Supabase")
    parser.parse_args()
    upload()


if __name__ == "__main__":
    main()

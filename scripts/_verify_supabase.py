from __future__ import annotations

import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SECRET_KEY") or ""


def _headers() -> dict[str, str]:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL is required")
    if not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY or SUPABASE_SECRET_KEY is required")
    return {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}


def main() -> None:
    headers = _headers()

    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/dataset_runs?select=id,wallet,label,status,stats,created_at&limit=5",
        headers=headers,
        timeout=10,
    )
    response.raise_for_status()
    for run in response.json():
        print(f"Run: {run['id'][:8]}... | {run['label']} | {run['status']} | {run['created_at']}")
        print(f"  Stats: {json.dumps(run['stats'])}")

    artifacts_response = requests.get(
        f"{SUPABASE_URL}/rest/v1/dataset_artifacts?select=artifact_type,file_name,row_count,sha256&limit=10",
        headers=headers,
        timeout=10,
    )
    artifacts_response.raise_for_status()
    for artifact in artifacts_response.json():
        print(f"  Artifact: {artifact['artifact_type']} | {artifact['file_name']} | {artifact['row_count']} rows")


if __name__ == "__main__":
    main()

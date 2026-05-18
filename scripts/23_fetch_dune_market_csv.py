#!/usr/bin/env python3
"""Run a Dune query and download its CSV result.

This helper keeps secrets out of the repository:
- reads DUNE_API_KEY from env or .env
- writes only the exported CSV

Typical flow:
1. Create a Dune query from sql/dune_market_same_token_swaps.sql.
2. Put target mints into the query in Dune.
3. Run this script with the query id.
4. Feed the CSV into scripts/21_build_market_same_token_swaps.py.
"""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

from common import ensure_dirs

load_dotenv()

DUNE_API_BASE = "https://api.dune.com/api/v1"


def api_key() -> str:
    key = os.getenv("DUNE_API_KEY", "").strip()
    if not key:
        raise RuntimeError("DUNE_API_KEY is required in env/.env")
    return key


def headers() -> dict[str, str]:
    return {"X-Dune-API-Key": api_key()}


def execute_query(query_id: int, performance: str | None = None) -> str:
    payload: dict[str, Any] = {}
    if performance:
        payload["performance"] = performance
    url = f"{DUNE_API_BASE}/query/{query_id}/execute"
    response = requests.post(url, json=payload, headers=headers(), timeout=60)
    response.raise_for_status()
    data = response.json()
    execution_id = data.get("execution_id")
    if not execution_id:
        raise RuntimeError(f"Dune response did not include execution_id: {data}")
    return str(execution_id)


def poll_execution(execution_id: str, interval_seconds: float, timeout_seconds: int) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    url = f"{DUNE_API_BASE}/execution/{execution_id}/status"
    last: dict[str, Any] = {}
    while time.time() < deadline:
        response = requests.get(url, headers=headers(), timeout=30)
        response.raise_for_status()
        last = response.json()
        state = str(last.get("state") or "").upper()
        if state in {"QUERY_STATE_COMPLETED", "COMPLETED"}:
            return last
        if state in {"QUERY_STATE_FAILED", "FAILED", "QUERY_STATE_CANCELLED", "CANCELLED"}:
            raise RuntimeError(f"Dune execution failed: {last}")
        time.sleep(interval_seconds)
    raise TimeoutError(f"Timed out waiting for Dune execution {execution_id}; last={last}")


def download_csv(execution_id: str, output: Path) -> None:
    url = f"{DUNE_API_BASE}/execution/{execution_id}/results/csv"
    response = requests.get(url, headers=headers(), timeout=180)
    response.raise_for_status()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(response.content)


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute Dune query and download CSV")
    parser.add_argument("--query-id", type=int, required=True)
    parser.add_argument("--output", default="data/external/dune_market_same_token_swaps.csv")
    parser.add_argument("--performance", default=None, help="Optional Dune performance tier, e.g. medium/large if enabled")
    parser.add_argument("--poll-interval", type=float, default=5.0)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--execution-id", default="", help="Skip execute step and download an existing execution_id")
    args = parser.parse_args()

    ensure_dirs()
    execution_id = args.execution_id.strip() or execute_query(args.query_id, args.performance)
    if not args.execution_id.strip():
        status = poll_execution(execution_id, args.poll_interval, args.timeout)
        print(f"[OK] Dune execution completed: {execution_id}; state={status.get('state')}")
    download_csv(execution_id, Path(args.output))
    print(f"[OK] downloaded CSV to {args.output}")


if __name__ == "__main__":
    main()

"""Shared helpers for the membot forensic dataset pipeline.

The helpers here intentionally prefer explicit UNKNOWN / empty outputs over
silent fake metrics. They do not store secrets and read RPC settings from env.
"""

from __future__ import annotations

import csv
import json
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests
from dotenv import load_dotenv

load_dotenv()

LAMPORTS_PER_SOL = 1_000_000_000
TARGET_WALLET = os.getenv("TARGET_WALLET", "7BNaxx6KdUYrjACNQZ9He26NBFoFxujQMAfNLnArLGH5")
RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
COMMITMENT = os.getenv("SOLANA_COMMITMENT", "finalized")
REQUEST_SLEEP_SECONDS = float(os.getenv("REQUEST_SLEEP_SECONDS", "0.15"))
RPC_MAX_RETRIES = int(os.getenv("RPC_MAX_RETRIES", "6"))
RPC_BACKOFF_BASE_SECONDS = float(os.getenv("RPC_BACKOFF_BASE_SECONDS", "0.75"))
RPC_BACKOFF_MAX_SECONDS = float(os.getenv("RPC_BACKOFF_MAX_SECONDS", "20"))
RPC_TIMEOUT_SECONDS = int(os.getenv("RPC_TIMEOUT_SECONDS", "45"))
RPC_JITTER_SECONDS = float(os.getenv("RPC_JITTER_SECONDS", "0.35"))

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_PARSED = ROOT / "data" / "parsed"
DATA_PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dirs() -> None:
    for path in (DATA_RAW, DATA_PARSED, DATA_PROCESSED, REPORTS):
        path.mkdir(parents=True, exist_ok=True)


def _retry_delay(attempt: int) -> float:
    base = min(RPC_BACKOFF_MAX_SECONDS, RPC_BACKOFF_BASE_SECONDS * (2 ** max(attempt - 1, 0)))
    jitter = random.uniform(0, max(RPC_JITTER_SECONDS, 0.0)) if RPC_JITTER_SECONDS > 0 else 0.0
    return base + jitter


def rpc_call(method: str, params: list[Any], timeout: int | None = None, max_retries: int | None = None) -> Any:
    """Call a Solana JSON-RPC method and return result.

    Uses bounded exponential backoff for transient provider failures, especially
    public RPC 429 rate limits. Secrets are never embedded here; configure
    `SOLANA_RPC_URL` through environment/GitHub secrets/Streamlit secrets.
    """
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    retries = RPC_MAX_RETRIES if max_retries is None else max_retries
    request_timeout = RPC_TIMEOUT_SECONDS if timeout is None else timeout
    last_error: Exception | None = None

    for attempt in range(retries + 1):
        try:
            response = requests.post(RPC_URL, json=payload, timeout=request_timeout)
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else _retry_delay(attempt + 1)
                raise requests.HTTPError(f"429 Too Many Requests; retry_after={delay:.2f}s", response=response)
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                error = data["error"]
                code = error.get("code") if isinstance(error, dict) else None
                if code in {-32005, -32004, -32603} and attempt < retries:
                    delay = _retry_delay(attempt + 1)
                    print(f"[WARN] transient RPC error for {method}: {error}; retrying in {delay:.2f}s")
                    time.sleep(delay)
                    continue
                raise RuntimeError(f"RPC error for {method}: {error}")
            return data.get("result")
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as exc:
            last_error = exc
            if attempt >= retries:
                break
            delay = _retry_delay(attempt + 1)
            print(f"[WARN] RPC transport error for {method}: {exc}; retrying in {delay:.2f}s")
            time.sleep(delay)

    raise RuntimeError(f"RPC call failed after {retries + 1} attempts for {method}: {last_error}")


def polite_sleep() -> None:
    if REQUEST_SLEEP_SECONDS > 0:
        time.sleep(REQUEST_SLEEP_SECONDS)


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def as_int(value: Any, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default

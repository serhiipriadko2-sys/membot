"""Shared helpers for the membot forensic dataset pipeline.

The helpers here intentionally prefer explicit UNKNOWN / empty outputs over
silent fake metrics. They do not store secrets and read RPC settings from env.
"""

from __future__ import annotations

import csv
import json
import os
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


def rpc_call(method: str, params: list[Any], timeout: int = 30) -> Any:
    """Call a Solana JSON-RPC method and return result."""
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    response = requests.post(RPC_URL, json=payload, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        raise RuntimeError(f"RPC error for {method}: {data['error']}")
    return data.get("result")


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

#!/usr/bin/env python3
"""Step 00 — RPC health gate.

Probes every configured Solana RPC endpoint and reports reachability,
RPC version, latest slot, and feature support.  Exits with code 0 only
if at least one provider is fully reachable.  Run this before
01_fetch_signatures.py so the pipeline never starts a doomed fetch.

Outputs:
  data/raw/rpc_health.json   — structured probe results
  stdout                     — human-readable table

Environment variables checked (in priority order):
  SOLANA_RPC_URL, HELIUS_RPC_URL, QUICKNODE_RPC_URL,
  TRITON_RPC_URL, CUSTOM_RPC_URL

Usage:
  python scripts/00_check_rpc_health.py
  python scripts/00_check_rpc_health.py --json-only
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass  # stdlib-only fallback: read env from shell

# ---------------------------------------------------------------------------
# Paths (mirror common.py layout but avoid importing it so this script
# can run even if common.py has dependency issues)
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------
PROVIDER_ENV_KEYS: list[tuple[str, str]] = [
    ("SOLANA_RPC_URL",   "solana-public"),
    ("HELIUS_RPC_URL",   "helius"),
    ("QUICKNODE_RPC_URL", "quicknode"),
    ("TRITON_RPC_URL",   "triton"),
    ("CUSTOM_RPC_URL",   "custom"),
]

# Fallback if nothing is set at all
DEFAULT_PUBLIC_RPC = "https://api.mainnet-beta.solana.com"


def _rpc_post(url: str, method: str, params: list | None = None, timeout: int = 10) -> dict:
    """Low-level JSON-RPC POST using only stdlib."""
    body = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or [],
    }).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def probe_endpoint(url: str) -> dict:
    """Probe a single RPC endpoint and return a structured result."""
    result: dict = {
        "url": url,
        "reachable": False,
        "http_status": None,
        "rpc_version": None,
        "latest_slot": None,
        "supports_getTransaction": None,
        "rate_limit_hint": None,
        "latency_ms": None,
        "error": None,
    }

    # --- getVersion (basic reachability + version) ---
    try:
        t0 = time.monotonic()
        version_resp = _rpc_post(url, "getVersion")
        latency_ms = round((time.monotonic() - t0) * 1000, 1)
        result["latency_ms"] = latency_ms
        result["http_status"] = 200
        result["reachable"] = True
        ver = version_resp.get("result", {})
        result["rpc_version"] = ver.get("solana-core", "UNKNOWN")
    except urllib.error.HTTPError as exc:
        result["http_status"] = exc.code
        result["error"] = f"HTTP {exc.code}: {exc.reason}"
        return result
    except urllib.error.URLError as exc:
        result["error"] = str(exc.reason)
        return result
    except Exception as exc:
        result["error"] = repr(exc)
        return result

    # --- getSlot (latest confirmed slot) ---
    try:
        slot_resp = _rpc_post(url, "getSlot", [{"commitment": "finalized"}])
        result["latest_slot"] = slot_resp.get("result")
    except Exception:
        result["latest_slot"] = "UNAVAILABLE"

    # --- getTransaction capability check ---
    # We use a known-invalid signature to see if the method is supported
    # (returns null) vs. blocked (returns 403/method-not-allowed).
    try:
        dummy_sig = "1" * 88  # syntactically valid but non-existent
        tx_resp = _rpc_post(
            url,
            "getTransaction",
            [dummy_sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}],
        )
        # If we get here the method is supported (result will be null for a fake sig)
        if "error" in tx_resp:
            err = tx_resp["error"]
            # -32601 = method not found;  -32602 = invalid params (method exists)
            code = err.get("code", 0) if isinstance(err, dict) else 0
            result["supports_getTransaction"] = code != -32601
        else:
            result["supports_getTransaction"] = True
    except Exception:
        result["supports_getTransaction"] = False

    # --- Rate-limit hint (check response headers if available) ---
    try:
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "getHealth"}).encode()
        req = urllib.request.Request(
            url, data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            rl_remaining = resp.headers.get("x-ratelimit-remaining")
            rl_limit = resp.headers.get("x-ratelimit-limit")
            if rl_remaining or rl_limit:
                result["rate_limit_hint"] = f"{rl_remaining or '?'}/{rl_limit or '?'} remaining"
            else:
                result["rate_limit_hint"] = "no headers"
    except Exception:
        result["rate_limit_hint"] = "probe failed"

    return result


def gather_endpoints() -> list[tuple[str, str]]:
    """Return (provider_name, url) pairs from env, in priority order."""
    endpoints: list[tuple[str, str]] = []
    for env_key, label in PROVIDER_ENV_KEYS:
        url = os.getenv(env_key, "").strip()
        if url:
            endpoints.append((label, url))

    # Always include the public RPC as the lowest-priority fallback
    seen_urls = {url for _, url in endpoints}
    if DEFAULT_PUBLIC_RPC not in seen_urls:
        endpoints.append(("solana-public-fallback", DEFAULT_PUBLIC_RPC))

    return endpoints


def format_table(results: list[dict]) -> str:
    """Render results as a human-readable table."""
    cols = [
        ("provider",               14),
        ("reachable",                9),
        ("http_status",              6),
        ("rpc_version",             18),
        ("latest_slot",             14),
        ("supports_getTransaction", 10),
        ("latency_ms",               8),
        ("rate_limit_hint",         22),
        ("error",                   40),
    ]
    header = " | ".join(name.ljust(width) for name, width in cols)
    sep = "-+-".join("-" * width for _, width in cols)
    lines = [header, sep]
    for r in results:
        row_vals = []
        for name, width in cols:
            val = r.get(name, "")
            if val is None:
                val = "—"
            elif isinstance(val, bool):
                val = "YES" if val else "NO"
            row_vals.append(str(val)[:width].ljust(width))
        lines.append(" | ".join(row_vals))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Solana RPC health gate")
    parser.add_argument("--json-only", action="store_true", help="Suppress table output")
    parser.add_argument("--output", default=str(DATA_RAW / "rpc_health.json"))
    args = parser.parse_args()

    endpoints = gather_endpoints()
    results: list[dict] = []

    for provider, url in endpoints:
        print(f"[probe] {provider}: {url} ...", end=" ", flush=True)
        r = probe_endpoint(url)
        r["provider"] = provider
        results.append(r)
        status = "OK" if r["reachable"] else f"FAIL ({r.get('error', '?')})"
        print(status)

    # --- Persist ---
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "probed_at": datetime.now(timezone.utc).isoformat(),
        "endpoints_checked": len(results),
        "any_reachable": any(r["reachable"] for r in results),
        "best_provider": next(
            (r["provider"] for r in results if r["reachable"] and r.get("supports_getTransaction")),
            None,
        ),
        "results": results,
    }
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[saved] {output_path}")

    # --- Table ---
    if not args.json_only:
        print()
        print(format_table(results))
        print()

    # --- Verdict ---
    if payload["any_reachable"]:
        best = payload["best_provider"]
        if best:
            print(f"[PASS] Best provider for pipeline: {best}")
        else:
            print("[WARN] Some endpoints reachable but none support getTransaction")
            sys.exit(2)
    else:
        print("[FAIL] No Solana RPC endpoint is reachable from this environment.")
        print("       Set a working URL in SOLANA_RPC_URL, HELIUS_RPC_URL, etc.")
        print("       See docs/RPC_PROVIDER_STRATEGY.md for guidance.")
        sys.exit(1)


if __name__ == "__main__":
    main()

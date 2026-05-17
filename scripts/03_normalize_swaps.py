#!/usr/bin/env python3
"""Normalize raw Solana transactions into wallet-centric swap rows.

This is a balance-delta MVP parser. Ambiguous rows are preserved with lowered confidence
instead of being silently upgraded into facts.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from typing import Any

from common import DATA_PROCESSED, DATA_RAW, LAMPORTS_PER_SOL, TARGET_WALLET, as_float, ensure_dirs, read_json, write_csv

WSOL_MINT = "So11111111111111111111111111111111111111112"
FIELDS = [
    "wallet", "signature", "slot", "block_time", "token_mint", "side",
    "token_amount", "sol_amount", "price_sol", "source_programs",
    "fee_lamports", "is_failed", "parse_confidence", "notes",
]


def token_amount(tb: dict[str, Any]) -> float:
    ui = tb.get("uiTokenAmount") or {}
    if ui.get("uiAmountString") not in (None, ""):
        return as_float(ui.get("uiAmountString"))
    raw = as_float(ui.get("amount"))
    decimals = int(ui.get("decimals") or 0)
    return raw / (10 ** decimals) if decimals else raw


def token_deltas(meta: dict[str, Any], wallet: str) -> dict[str, float]:
    pre = defaultdict(float)
    post = defaultdict(float)
    for tb in meta.get("preTokenBalances") or []:
        if tb.get("owner") == wallet:
            pre[tb.get("mint", "")] += token_amount(tb)
    for tb in meta.get("postTokenBalances") or []:
        if tb.get("owner") == wallet:
            post[tb.get("mint", "")] += token_amount(tb)
    return {mint: post[mint] - pre[mint] for mint in set(pre) | set(post) if mint}


def account_keys(tx_result: dict[str, Any]) -> list[str]:
    message = tx_result.get("transaction", {}).get("message", {})
    keys = []
    for key in message.get("accountKeys") or []:
        if isinstance(key, str):
            keys.append(key)
        elif isinstance(key, dict):
            keys.append(key.get("pubkey", ""))
    return keys


def native_sol_delta(tx_result: dict[str, Any], wallet: str) -> float:
    meta = tx_result.get("meta") or {}
    keys = account_keys(tx_result)
    if wallet not in keys:
        return 0.0
    idx = keys.index(wallet)
    pre = meta.get("preBalances") or []
    post = meta.get("postBalances") or []
    if idx >= len(pre) or idx >= len(post):
        return 0.0
    delta = (float(post[idx]) - float(pre[idx])) / LAMPORTS_PER_SOL
    if keys and keys[0] == wallet:
        delta += float(meta.get("fee") or 0) / LAMPORTS_PER_SOL
    return delta


def collect_programs(tx_result: dict[str, Any]) -> str:
    message = tx_result.get("transaction", {}).get("message", {})
    out = []
    for ins in message.get("instructions") or []:
        pid = ins.get("programId") or ""
        if pid and pid not in out:
            out.append(pid)
    return ";".join(out)


def normalize(wallet: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for wrapper in payload.get("items", []):
        tx_result = wrapper.get("result") or {}
        meta = tx_result.get("meta") or {}
        signature = wrapper.get("signature", "")
        if not tx_result:
            continue
        if meta.get("err"):
            rows.append({
                "wallet": wallet,
                "signature": signature,
                "slot": tx_result.get("slot", ""),
                "block_time": tx_result.get("blockTime", ""),
                "token_mint": "",
                "side": "FAILED",
                "token_amount": "",
                "sol_amount": "",
                "price_sol": "",
                "source_programs": collect_programs(tx_result),
                "fee_lamports": meta.get("fee", 0),
                "is_failed": "true",
                "parse_confidence": "high",
                "notes": f"tx_err={meta.get('err')}",
            })
            continue
        deltas = token_deltas(meta, wallet)
        wsol_delta = deltas.pop(WSOL_MINT, 0.0)
        total_sol_delta = native_sol_delta(tx_result, wallet) + wsol_delta
        nonzero = [(mint, delta) for mint, delta in deltas.items() if abs(delta) > 0]
        if not nonzero:
            continue
        confidence = "high" if len(nonzero) == 1 and total_sol_delta != 0 else "medium"
        for mint, delta in nonzero:
            side = "UNKNOWN"
            if delta > 0 and total_sol_delta < 0:
                side = "BUY"
            elif delta < 0 and total_sol_delta > 0:
                side = "SELL"
            token_amt = abs(delta)
            sol_amt = abs(total_sol_delta)
            rows.append({
                "wallet": wallet,
                "signature": signature,
                "slot": tx_result.get("slot", ""),
                "block_time": tx_result.get("blockTime", ""),
                "token_mint": mint,
                "side": side,
                "token_amount": token_amt,
                "sol_amount": sol_amt,
                "price_sol": (sol_amt / token_amt) if token_amt and sol_amt else "",
                "source_programs": collect_programs(tx_result),
                "fee_lamports": meta.get("fee", 0),
                "is_failed": "false",
                "parse_confidence": confidence if side != "UNKNOWN" else "low",
                "notes": f"changed_mints={len(nonzero)};wsol_delta={wsol_delta};native_sol_delta={native_sol_delta(tx_result, wallet)}",
            })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize raw transactions into wallet swap rows")
    parser.add_argument("--wallet", default=TARGET_WALLET)
    parser.add_argument("--input", default=str(DATA_RAW / "transactions_raw.json"))
    parser.add_argument("--output", default=str(DATA_PROCESSED / "wallet_swaps.csv"))
    args = parser.parse_args()

    ensure_dirs()
    payload = read_json(__import__("pathlib").Path(args.input), default={"items": []})
    rows = normalize(args.wallet, payload)
    write_csv(__import__("pathlib").Path(args.output), rows, FIELDS)
    print(f"[OK] wrote {len(rows)} normalized rows")


if __name__ == "__main__":
    main()

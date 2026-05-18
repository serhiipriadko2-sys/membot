#!/usr/bin/env python3
"""Audit priority fees, ComputeBudget usage, and Jito-tip candidates.

Inputs:
- data/raw/transactions_raw.json from scripts/02_fetch_transactions.py

Outputs:
- data/processed/priority_fee_jito_audit.csv
- reports/priority_fee_jito_audit_report.md

Guardrails:
- Jito bundle inclusion is not provable from a normal getTransaction payload.
- We detect only on-chain tip-transfer candidates to known/configured tip accounts.
- Unknown instructions are preserved as UNKNOWN rather than forced into MEV claims.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Any

from common import DATA_PROCESSED, DATA_RAW, LAMPORTS_PER_SOL, REPORTS, as_int, ensure_dirs, read_json, write_csv

COMPUTE_BUDGET_PROGRAM = "ComputeBudget111111111111111111111111111111"
SYSTEM_PROGRAM = "11111111111111111111111111111111"

# Jito tip accounts can rotate. This list is intentionally configurable and should be
# replaced/enriched by live getTipAccounts data when available.
DEFAULT_JITO_TIP_ACCOUNTS = {
    "96gYZGLnq8xNCLcnLh5ZyyCrZU3x6W3VFrW1ZuXRXLtG",
    "HFqU5x63VTqvQss8hp11i4wVV8bD44PvwucfZ2bU7gRe",
    "Cw8CFyM4tY2m8mHk7dTgN3Xh3DgBLYpM1ghsA1dQtVn",
    "ADaUMid9yfUytqMBX5f3GhW5LDN8Xyfkci9a1p3WbZUd",
    "DfXygSm4jCyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh",
    "ADuUkR2z8Z3h7e3mGk2yu4gsRk6XQy2Zynr6bQ4e5o7a",
    "DttWaMuVvTiduZRnguLFw9TzGQqW1wS4Gf7hK7N5s2b9",
    "3AVi9Tg9Uo68tJfuvoKvqKNWKkC5wPdSSdeBnizKZ6jT",
}

FIELDS = [
    "signature",
    "slot",
    "block_time",
    "base_fee_lamports",
    "base_fee_sol",
    "compute_units_consumed",
    "compute_unit_limit",
    "compute_unit_price_micro_lamports",
    "estimated_priority_fee_lamports",
    "estimated_priority_fee_sol",
    "jito_tip_lamports",
    "jito_tip_sol",
    "jito_tip_account",
    "has_jito_tip",
    "has_compute_budget_ix",
    "compute_budget_ix_count",
    "fee_bucket",
    "verdict",
    "notes",
]


def load_tip_accounts(path: Path | None) -> set[str]:
    accounts = set(DEFAULT_JITO_TIP_ACCOUNTS)
    if path and path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            value = line.strip()
            if value and not value.startswith("#"):
                accounts.add(value)
    return accounts


def all_instructions(tx: dict[str, Any]) -> list[dict[str, Any]]:
    result = tx.get("result") or {}
    transaction = result.get("transaction") or {}
    message = transaction.get("message") or {}
    instructions = list(message.get("instructions") or [])
    meta = result.get("meta") or {}
    for inner in meta.get("innerInstructions") or []:
        instructions.extend(inner.get("instructions") or [])
    return [ix for ix in instructions if isinstance(ix, dict)]


def program_id(ix: dict[str, Any]) -> str:
    return str(ix.get("programId") or ix.get("program_id") or "")


def parsed_type(ix: dict[str, Any]) -> str:
    parsed = ix.get("parsed") or {}
    if isinstance(parsed, dict):
        return str(parsed.get("type") or "")
    return ""


def parsed_info(ix: dict[str, Any]) -> dict[str, Any]:
    parsed = ix.get("parsed") or {}
    if isinstance(parsed, dict) and isinstance(parsed.get("info"), dict):
        return parsed["info"]
    return {}


def compute_budget_audit(ixs: list[dict[str, Any]]) -> tuple[int, int, int]:
    ix_count = 0
    cu_limit = 0
    cu_price = 0
    for ix in ixs:
        if program_id(ix) != COMPUTE_BUDGET_PROGRAM:
            continue
        ix_count += 1
        ptype = parsed_type(ix)
        info = parsed_info(ix)
        if ptype in {"setComputeUnitLimit", "setComputeUnitLimitInstruction"}:
            cu_limit = as_int(info.get("units") or info.get("computeUnitLimit"), cu_limit)
        elif ptype in {"setComputeUnitPrice", "setComputeUnitPriceInstruction"}:
            cu_price = as_int(info.get("microLamports") or info.get("computeUnitPrice"), cu_price)
        else:
            # Some RPC providers do not json-parse compute budget instructions. Keep
            # ix_count as evidence of ComputeBudget use even if values are unknown.
            pass
    return ix_count, cu_limit, cu_price


def detect_jito_tip(ixs: list[dict[str, Any]], tip_accounts: set[str]) -> tuple[int, str]:
    total = 0
    accounts: list[str] = []
    for ix in ixs:
        if program_id(ix) != SYSTEM_PROGRAM or parsed_type(ix) != "transfer":
            continue
        info = parsed_info(ix)
        destination = str(info.get("destination") or "")
        lamports = as_int(info.get("lamports"), 0)
        if destination in tip_accounts and lamports > 0:
            total += lamports
            accounts.append(destination)
    return total, ";".join(sorted(set(accounts)))


def fee_bucket(fee_lamports: int) -> str:
    if fee_lamports <= 5_000:
        return "base_fee_like"
    if fee_lamports <= 50_000:
        return "low_priority_fee"
    if fee_lamports <= 200_000:
        return "medium_priority_fee"
    return "high_priority_fee"


def verdict_for(has_cb: bool, priority_fee: int, jito_tip: int) -> str:
    if jito_tip > 0:
        return "JITO_TIP_DETECTED"
    if has_cb and priority_fee > 0:
        return "PRIORITY_FEE_BOT"
    if has_cb:
        return "COMPUTE_BUDGET_ONLY"
    return "NO_MEV_EVIDENCE"


def audit_item(item: dict[str, Any], tip_accounts: set[str]) -> dict[str, Any]:
    result = item.get("result") or {}
    meta = result.get("meta") or {}
    signature = item.get("signature") or ""
    slot = as_int(result.get("slot"), 0)
    block_time = as_int(result.get("blockTime"), 0)
    fee_lamports = as_int(meta.get("fee"), 0)
    consumed = as_int(meta.get("computeUnitsConsumed"), 0)
    ixs = all_instructions(item)
    cb_count, cu_limit, cu_price = compute_budget_audit(ixs)
    priority_fee = 0
    if cu_price > 0:
        units_for_estimate = cu_limit or consumed
        priority_fee = int((units_for_estimate * cu_price) / 1_000_000)
    jito_tip, jito_account = detect_jito_tip(ixs, tip_accounts)
    has_cb = cb_count > 0
    verdict = verdict_for(has_cb, priority_fee, jito_tip)
    notes = []
    if cb_count and not (cu_limit or cu_price):
        notes.append("compute_budget_ix_detected_but_not_json_parsed")
    if verdict == "NO_MEV_EVIDENCE":
        notes.append("normal_getTransaction_cannot_prove_absence_of_private_bundle")
    return {
        "signature": signature,
        "slot": slot,
        "block_time": block_time,
        "base_fee_lamports": fee_lamports,
        "base_fee_sol": f"{fee_lamports / LAMPORTS_PER_SOL:.12f}",
        "compute_units_consumed": consumed,
        "compute_unit_limit": cu_limit or "",
        "compute_unit_price_micro_lamports": cu_price or "",
        "estimated_priority_fee_lamports": priority_fee or "",
        "estimated_priority_fee_sol": f"{priority_fee / LAMPORTS_PER_SOL:.12f}" if priority_fee else "",
        "jito_tip_lamports": jito_tip or "",
        "jito_tip_sol": f"{jito_tip / LAMPORTS_PER_SOL:.12f}" if jito_tip else "",
        "jito_tip_account": jito_account,
        "has_jito_tip": "true" if jito_tip > 0 else "false",
        "has_compute_budget_ix": "true" if has_cb else "false",
        "compute_budget_ix_count": cb_count,
        "fee_bucket": fee_bucket(fee_lamports),
        "verdict": verdict,
        "notes": ";".join(notes),
    }


def render_report(rows: list[dict[str, Any]], input_path: Path) -> str:
    verdicts = Counter(str(row.get("verdict")) for row in rows)
    fee_buckets = Counter(str(row.get("fee_bucket")) for row in rows)
    cb_count = sum(1 for row in rows if str(row.get("has_compute_budget_ix")).lower() == "true")
    jito_count = sum(1 for row in rows if str(row.get("has_jito_tip")).lower() == "true")
    total_fee = sum(as_int(row.get("base_fee_lamports"), 0) for row in rows)
    total_tip = sum(as_int(row.get("jito_tip_lamports"), 0) for row in rows)
    lines = [
        "# Priority Fee / Jito Audit Report",
        "",
        "## Scope",
        "",
        f"- Input: `{input_path}`",
        f"- Transactions audited: `{len(rows)}`",
        "- Source: Solana `getTransaction` JSON payloads from local raw export.",
        "- Guardrail: this audit can detect on-chain tip-transfer candidates, but cannot prove private bundle inclusion without block-engine/bundle data.",
        "",
        "## Summary",
        "",
        f"- ComputeBudget instruction detected: `{cb_count}`",
        f"- Jito tip candidates detected: `{jito_count}`",
        f"- Total base fee SOL: `{total_fee / LAMPORTS_PER_SOL:.9f}`",
        f"- Total Jito tip SOL: `{total_tip / LAMPORTS_PER_SOL:.9f}`",
        "",
        "## Verdict counts",
        "",
    ]
    for key, value in sorted(verdicts.items()):
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Fee buckets", ""])
    for key, value in sorted(fee_buckets.items()):
        lines.append(f"- `{key}`: `{value}`")
    lines.extend([
        "",
        "## Notes",
        "",
        "- `PRIORITY_FEE_BOT` means ComputeBudget priority settings were visible or estimable.",
        "- `JITO_TIP_DETECTED` means a system transfer to a configured tip account was found.",
        "- `NO_MEV_EVIDENCE` is not proof that no MEV/private routing occurred.",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit priority fees and Jito tip candidates")
    parser.add_argument("--transactions", default=str(DATA_RAW / "transactions_raw.json"))
    parser.add_argument("--tip-accounts", default="", help="Optional newline-separated Jito tip accounts file")
    parser.add_argument("--output", default=str(DATA_PROCESSED / "priority_fee_jito_audit.csv"))
    parser.add_argument("--report", default=str(REPORTS / "priority_fee_jito_audit_report.md"))
    args = parser.parse_args()

    ensure_dirs()
    input_path = Path(args.transactions)
    payload = read_json(input_path, default={"items": []})
    tip_accounts = load_tip_accounts(Path(args.tip_accounts) if args.tip_accounts else None)
    items = payload.get("items", []) if isinstance(payload, dict) else []
    rows = [audit_item(item, tip_accounts) for item in items if isinstance(item, dict)]
    write_csv(Path(args.output), rows, FIELDS)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(rows, input_path), encoding="utf-8")
    print(f"[OK] wrote {len(rows)} priority/Jito audit rows to {args.output}")
    print(f"[OK] wrote report to {args.report}")


if __name__ == "__main__":
    main()

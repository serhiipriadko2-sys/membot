#!/usr/bin/env python3
"""Test entry/exit hypotheses against processed wallet datasets.

This script is deliberately conservative:
- every threshold in configs/entry_exit_hypotheses.v0.yaml is treated as HYP;
- missing columns produce UNKNOWN rather than fabricated evidence;
- synthetic-looking rows are counted and flagged;
- outputs support/unknown rates, not final algorithm claims.

Default outputs:
- data/processed/entry_exit_hypothesis_tests.csv
- reports/entry_exit_hypothesis_report.md
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

from common import DATA_PROCESSED, REPORTS, as_float, ensure_dirs, read_csv, write_csv

UNKNOWN = "UNKNOWN"
EPS = 1e-12

FIELDS = [
    "hypothesis_id",
    "scope",
    "status",
    "verdict",
    "support_rate_pct",
    "known_rows",
    "total_rows",
    "missing_rows",
    "synthetic_suspect_rows",
    "columns_used",
    "threshold",
    "median_value",
    "mean_value",
    "notes",
]

DEFAULT_CONFIG = Path("configs/entry_exit_hypotheses.v0.yaml")


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    text = path.read_text(encoding="utf-8")
    return json.loads(text)


def is_known(value: Any) -> bool:
    return value not in (None, "", UNKNOWN)


def first_known(row: dict[str, str], names: list[str]) -> tuple[str, str]:
    for name in names:
        value = row.get(name)
        if is_known(value):
            return name, str(value)
    return "", ""


def parse_bool(value: Any) -> bool | None:
    if not is_known(value):
        return None
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "revoked", "disabled", "success", "pass"}:
        return True
    if text in {"0", "false", "no", "n", "enabled", "failed", "fail"}:
        return False
    return None


def is_synthetic_row(row: dict[str, str]) -> bool:
    token = str(row.get("token") or row.get("token_symbol") or row.get("token_mint") or "")
    tx = str(row.get("tx_id") or row.get("tx_hash") or row.get("signature") or "")
    wallet_type = str(row.get("wallet_type") or "").lower()
    if token.startswith("MEME_"):
        return True
    if wallet_type in {"smart_money", "retail", "whale"} and len(tx) < 32:
        return True
    if tx.startswith(("1KmN", "2PqR", "3KmN", "4PqR", "5KmN", "6PqR", "7KmN", "8PqR", "9KmN")):
        return True
    return False


def numeric_values(rows: list[dict[str, str]], columns: list[str]) -> tuple[list[float], str, int]:
    values: list[float] = []
    used_counts: dict[str, int] = defaultdict(int)
    missing = 0
    for row in rows:
        col, raw = first_known(row, columns)
        if not col:
            missing += 1
            continue
        value = as_float(raw, math.nan)
        if math.isfinite(value):
            values.append(value)
            used_counts[col] += 1
        else:
            missing += 1
    used = ";".join(f"{k}:{v}" for k, v in sorted(used_counts.items()))
    return values, used, missing


def bool_values(rows: list[dict[str, str]], columns: list[str]) -> tuple[list[bool], str, int]:
    values: list[bool] = []
    used_counts: dict[str, int] = defaultdict(int)
    missing = 0
    for row in rows:
        col, raw = first_known(row, columns)
        if not col:
            missing += 1
            continue
        value = parse_bool(raw)
        if value is None:
            missing += 1
            continue
        values.append(value)
        used_counts[col] += 1
    used = ";".join(f"{k}:{v}" for k, v in sorted(used_counts.items()))
    return values, used, missing


def median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def verdict_from_rate(rate: float, known_rows: int, total_rows: int) -> str:
    if known_rows == 0:
        return "UNKNOWN"
    coverage = known_rows / total_rows if total_rows else 0.0
    if coverage < 0.50:
        return "UNKNOWN"
    if rate >= 0.80:
        return "PASS_HYP"
    if rate >= 0.60:
        return "PARTIAL_HYP"
    return "NO_SUPPORT"


def threshold_text(spec: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ["min", "max", "expected", "profit_below", "activate_after_profit_pct", "max_drawdown_from_peak_pct", "min_sell_legs"]:
        if key in spec:
            parts.append(f"{key}={spec[key]}")
    return ", ".join(parts)


def build_result(
    hypothesis_id: str,
    scope: str,
    status: str,
    verdict: str,
    support_rate: float,
    known_rows: int,
    total_rows: int,
    missing_rows: int,
    synthetic_rows: int,
    columns_used: str,
    threshold: str,
    values: list[float],
    notes: str,
) -> dict[str, Any]:
    return {
        "hypothesis_id": hypothesis_id,
        "scope": scope,
        "status": status,
        "verdict": verdict,
        "support_rate_pct": f"{support_rate * 100:.2f}" if known_rows else "",
        "known_rows": known_rows,
        "total_rows": total_rows,
        "missing_rows": missing_rows,
        "synthetic_suspect_rows": synthetic_rows,
        "columns_used": columns_used,
        "threshold": threshold,
        "median_value": f"{median(values):.8f}" if values else "",
        "mean_value": f"{mean(values):.8f}" if values else "",
        "notes": notes,
    }


def test_numeric_range(hid: str, spec: dict[str, Any], rows: list[dict[str, str]], scope: str) -> dict[str, Any]:
    values, used, missing = numeric_values(rows, spec.get("columns", []))
    min_value = spec.get("min")
    max_value = spec.get("max")
    supported = 0
    for value in values:
        ok = True
        if min_value is not None:
            ok = ok and value >= float(min_value)
        if max_value is not None:
            ok = ok and value <= float(max_value)
        supported += 1 if ok else 0
    rate = supported / len(values) if values else 0.0
    return build_result(
        hid,
        scope,
        spec.get("status", "HYP"),
        verdict_from_rate(rate, len(values), len(rows)),
        rate,
        len(values),
        len(rows),
        missing,
        sum(1 for row in rows if is_synthetic_row(row)),
        used,
        threshold_text(spec),
        values,
        spec.get("description", ""),
    )


def test_bool_expected(hid: str, spec: dict[str, Any], rows: list[dict[str, str]], scope: str) -> dict[str, Any]:
    values, used, missing = bool_values(rows, spec.get("columns", []))
    expected = bool(spec.get("expected"))
    supported = sum(1 for value in values if value is expected)
    rate = supported / len(values) if values else 0.0
    numeric = [1.0 if value else 0.0 for value in values]
    return build_result(
        hid,
        scope,
        spec.get("status", "RAW_REQUIRED"),
        verdict_from_rate(rate, len(values), len(rows)),
        rate,
        len(values),
        len(rows),
        missing,
        sum(1 for row in rows if is_synthetic_row(row)),
        used,
        threshold_text(spec),
        numeric,
        spec.get("description", ""),
    )


def return_pct(row: dict[str, str], pct_columns: list[str] | None = None) -> float | None:
    for name in pct_columns or ["pnl_pct", "net_pnl_pct", "return_pct"]:
        if is_known(row.get(name)):
            value = as_float(row.get(name), math.nan)
            if math.isfinite(value):
                # Accept either decimal or percent form.
                return value / 100 if abs(value) > 2 else value
    pnl = as_float(row.get("net_pnl_sol") or row.get("pnl_sol"), math.nan)
    entry = as_float(row.get("entry_sol"), math.nan)
    if math.isfinite(pnl) and math.isfinite(entry) and abs(entry) > EPS:
        return pnl / entry
    return None


def test_hard_stop(hid: str, spec: dict[str, Any], trades: list[dict[str, str]]) -> dict[str, Any]:
    values: list[float] = []
    supported = 0
    for row in trades:
        pct = return_pct(row, spec.get("columns"))
        if pct is None:
            continue
        if pct < 0:
            values.append(pct)
            if float(spec.get("min", -0.20)) <= pct <= float(spec.get("max", -0.10)):
                supported += 1
    rate = supported / len(values) if values else 0.0
    return build_result(
        hid,
        "exit",
        spec.get("status", "HYP_THRESHOLD"),
        verdict_from_rate(rate, len(values), len(trades)),
        rate,
        len(values),
        len(trades),
        len(trades) - len(values),
        sum(1 for row in trades if is_synthetic_row(row)),
        "pnl_pct|net_pnl_pct|return_pct|pnl_sol/entry_sol",
        threshold_text(spec),
        values,
        spec.get("description", ""),
    )


def test_time_stop(hid: str, spec: dict[str, Any], trades: list[dict[str, str]]) -> dict[str, Any]:
    values: list[float] = []
    supported = 0
    for row in trades:
        hold = as_float(row.get("hold_seconds"), math.nan)
        pct = return_pct(row, spec.get("columns"))
        if not math.isfinite(hold) or pct is None:
            continue
        weak = pct < float(spec.get("profit_below", 0.02))
        if weak:
            values.append(hold)
            if float(spec.get("min", 180)) <= hold <= float(spec.get("max", 300)):
                supported += 1
    rate = supported / len(values) if values else 0.0
    return build_result(
        hid,
        "exit",
        spec.get("status", "HYP_THRESHOLD"),
        verdict_from_rate(rate, len(values), len(trades)),
        rate,
        len(values),
        len(trades),
        len(trades) - len(values),
        sum(1 for row in trades if is_synthetic_row(row)),
        "hold_seconds + pnl_pct|pnl_sol/entry_sol",
        threshold_text(spec),
        values,
        spec.get("description", ""),
    )


def test_trailing(hid: str, spec: dict[str, Any], trades: list[dict[str, str]]) -> dict[str, Any]:
    supported = 0
    values: list[float] = []
    for row in trades:
        max_pnl = None
        drawdown = None
        if is_known(row.get("max_unrealized_pnl_pct")):
            max_pnl = as_float(row.get("max_unrealized_pnl_pct"), math.nan)
            max_pnl = max_pnl / 100 if abs(max_pnl) > 2 else max_pnl
        if is_known(row.get("drawdown_from_peak_pct")):
            drawdown = as_float(row.get("drawdown_from_peak_pct"), math.nan)
            drawdown = drawdown / 100 if abs(drawdown) > 2 else drawdown
        if max_pnl is None or drawdown is None or not math.isfinite(max_pnl) or not math.isfinite(drawdown):
            continue
        values.append(drawdown)
        if max_pnl >= float(spec.get("activate_after_profit_pct", 0.50)) and drawdown <= float(spec.get("max_drawdown_from_peak_pct", 0.15)):
            supported += 1
    rate = supported / len(values) if values else 0.0
    return build_result(
        hid,
        "exit",
        spec.get("status", "RAW_REQUIRED"),
        verdict_from_rate(rate, len(values), len(trades)),
        rate,
        len(values),
        len(trades),
        len(trades) - len(values),
        sum(1 for row in trades if is_synthetic_row(row)),
        "max_unrealized_pnl_pct;drawdown_from_peak_pct",
        threshold_text(spec),
        values,
        spec.get("description", "") + " Requires intra-trade price path; UNKNOWN is expected until path data exists.",
    )


def test_scaling_out(hid: str, spec: dict[str, Any], swaps: list[dict[str, str]], trades: list[dict[str, str]]) -> dict[str, Any]:
    sell_counts: dict[str, int] = defaultdict(int)
    source_rows = swaps if swaps else trades
    for row in source_rows:
        side = str(row.get("side") or "").upper()
        mint = row.get("token_mint") or row.get("mint") or row.get("token") or ""
        if side == "SELL" and mint:
            sell_counts[mint] += 1
        elif not side and row.get("exit_signature") and mint:
            sell_counts[mint] += 1
    values = [float(count) for count in sell_counts.values()]
    min_legs = int(spec.get("min_sell_legs", 2))
    supported = sum(1 for count in values if count >= min_legs)
    total = len(values) if values else len(source_rows)
    rate = supported / len(values) if values else 0.0
    return build_result(
        hid,
        "exit",
        spec.get("status", "HYP_THRESHOLD"),
        verdict_from_rate(rate, len(values), total),
        rate,
        len(values),
        total,
        max(0, total - len(values)),
        sum(1 for row in source_rows if is_synthetic_row(row)),
        "wallet_swaps.side/token_mint or trades.exit_signature/token_mint",
        threshold_text(spec),
        values,
        spec.get("description", ""),
    )


def test_open_tail(hid: str, spec: dict[str, Any], rows: list[dict[str, str]]) -> dict[str, Any]:
    values: list[float] = []
    supported = 0
    for row in rows:
        status = str(row.get("position_status") or row.get("status") or "").lower()
        amount = as_float(row.get("open_token_amount") or row.get("remaining_tokens"), 0.0)
        if not status and amount <= 0:
            continue
        is_open = status in {"open", "partial", "tail_open"} or amount > 0
        values.append(1.0 if is_open else 0.0)
        if is_open:
            supported += 1
    rate = supported / len(values) if values else 0.0
    return build_result(
        hid,
        "exit",
        spec.get("status", "HYP_THRESHOLD"),
        verdict_from_rate(rate, len(values), len(rows)),
        rate,
        len(values),
        len(rows),
        len(rows) - len(values),
        sum(1 for row in rows if is_synthetic_row(row)),
        "open_token_amount|remaining_tokens|position_status",
        threshold_text(spec),
        values,
        spec.get("description", ""),
    )


def run_tests(config: dict[str, Any], entry_rows: list[dict[str, str]], trades: list[dict[str, str]], swaps: list[dict[str, str]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for hid, spec in config.get("entry", {}).items():
        direction = spec.get("direction")
        if direction == "bool_expected":
            results.append(test_bool_expected(hid, spec, entry_rows, "entry"))
        else:
            results.append(test_numeric_range(hid, spec, entry_rows, "entry"))

    for hid, spec in config.get("exit", {}).items():
        direction = spec.get("direction")
        if direction == "loss_inside_range":
            results.append(test_hard_stop(hid, spec, trades))
        elif direction == "time_stop_fit":
            results.append(test_time_stop(hid, spec, trades))
        elif direction == "trailing_fit":
            results.append(test_trailing(hid, spec, trades))
        elif direction == "multi_sell_leg_detected":
            results.append(test_scaling_out(hid, spec, swaps, trades))
        elif direction == "open_tail_detected":
            results.append(test_open_tail(hid, spec, trades))
        else:
            results.append(test_numeric_range(hid, spec, trades, "exit"))
    return results


def render_report(results: list[dict[str, Any]], config_path: Path, entry_count: int, trade_count: int, swap_count: int) -> str:
    verdict_counts: dict[str, int] = defaultdict(int)
    unknowns: list[dict[str, Any]] = []
    supported: list[dict[str, Any]] = []
    synthetic_total = 0
    for row in results:
        verdict_counts[str(row["verdict"])] += 1
        synthetic_total += int(row.get("synthetic_suspect_rows") or 0)
        if row["verdict"] == "UNKNOWN":
            unknowns.append(row)
        if row["verdict"] in {"PASS_HYP", "PARTIAL_HYP"}:
            supported.append(row)

    lines = [
        "# Entry/Exit Hypothesis Test Report",
        "",
        "## Scope",
        "",
        f"- Config: `{config_path}`",
        f"- Entry rows: `{entry_count}`",
        f"- Paired trade rows: `{trade_count}`",
        f"- Wallet swap rows: `{swap_count}`",
        "- Verdicts are hypothesis support only, not final claims about the wallet.",
        "- Synthetic-looking rows are flagged and must not be used for wallet-specific forensic claims.",
        "",
        "## Verdict counts",
        "",
    ]
    for verdict in sorted(verdict_counts):
        lines.append(f"- `{verdict}`: `{verdict_counts[verdict]}`")
    lines.extend(["", "## Supported hypotheses", ""])
    if supported:
        for row in supported:
            lines.append(f"- `{row['hypothesis_id']}`: `{row['verdict']}` at `{row['support_rate_pct']}%` support; known `{row['known_rows']}/{row['total_rows']}`.")
    else:
        lines.append("- None.")
    lines.extend(["", "## Unknown / missing-data hypotheses", ""])
    if unknowns:
        for row in unknowns:
            lines.append(f"- `{row['hypothesis_id']}`: missing `{row['missing_rows']}/{row['total_rows']}` rows; needs `{row['columns_used'] or row['threshold']}`.")
    else:
        lines.append("- None.")
    lines.extend(["", "## Synthetic guard", ""])
    lines.append(f"- Synthetic suspect row count across tests: `{synthetic_total}`")
    if synthetic_total:
        lines.append("- Guardrail: do not use this run for wallet-specific forensic claims until synthetic fixtures are removed.")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Test entry/exit hypotheses from config")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--entry-context", default=str(DATA_PROCESSED / "entry_context_market.csv"))
    parser.add_argument("--fallback-entry-context", default=str(DATA_PROCESSED / "entry_context.csv"))
    parser.add_argument("--trades", default=str(DATA_PROCESSED / "trades_paired.csv"))
    parser.add_argument("--swaps", default=str(DATA_PROCESSED / "wallet_swaps.csv"))
    parser.add_argument("--output", default=str(DATA_PROCESSED / "entry_exit_hypothesis_tests.csv"))
    parser.add_argument("--report", default=str(REPORTS / "entry_exit_hypothesis_report.md"))
    args = parser.parse_args()

    ensure_dirs()
    config_path = Path(args.config)
    config = load_config(config_path)
    entry_path = Path(args.entry_context)
    entry_rows = read_csv(entry_path)
    if not entry_rows:
        entry_rows = read_csv(Path(args.fallback_entry_context))
    trades = read_csv(Path(args.trades))
    swaps = read_csv(Path(args.swaps))
    results = run_tests(config, entry_rows, trades, swaps)
    write_csv(Path(args.output), results, FIELDS)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(results, config_path, len(entry_rows), len(trades), len(swaps)), encoding="utf-8")
    print(f"[OK] wrote {len(results)} hypothesis tests to {args.output}")
    print(f"[OK] wrote report to {args.report}")


if __name__ == "__main__":
    main()

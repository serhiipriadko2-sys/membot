#!/usr/bin/env python3
"""Evaluate the Observer live-run latency gate.

The evaluator is intentionally stricter than the dashboard wording. A status
line can say "ACTIVE / GATE FAILED", but Paper mode is blocked until the raw
latency CSV proves coverage and timing with the mandatory breakdown fields.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
DEFAULT_INPUT = ROOT / "data" / "processed" / "observer_latency_live.csv"
DEFAULT_REPORT = ROOT / "reports" / "observer_gate_report.md"
DEFAULT_JSON = ROOT / "reports" / "observer_gate_report.json"

REQUIRED_FIELDS = [
    "signal_ts_ms",
    "detected_ts_ms",
    "quote_start_ts_ms",
    "quote_end_ts_ms",
    "detector_latency_ms",
    "quote_latency_ms",
    "total_latency_ms",
    "quote_ok",
    "error",
]

NUMERIC_FIELDS = [
    "signal_ts_ms",
    "detected_ts_ms",
    "quote_start_ts_ms",
    "quote_end_ts_ms",
    "detector_latency_ms",
    "quote_latency_ms",
    "total_latency_ms",
]

TRUE_VALUES = {"1", "true", "yes", "y", "ok", "success"}


def parse_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_bool(value: Any) -> bool:
    return str(value).strip().lower() in TRUE_VALUES


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    idx = (len(ordered) - 1) * q
    lower = math.floor(idx)
    upper = math.ceil(idx)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (idx - lower)


def read_latency_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def round_metric(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 3)


def evaluate_rows(
    rows: list[dict[str, Any]],
    *,
    fieldnames: list[str] | None = None,
    run_mode: str = "live",
    min_live_rows: int = 50,
    coverage_target_pct: float = 90.0,
    p50_total_target_ms: float = 500.0,
    p90_total_target_ms: float = 1000.0,
) -> dict[str, Any]:
    fields = fieldnames if fieldnames is not None else list(rows[0].keys()) if rows else []
    missing_fields = [field for field in REQUIRED_FIELDS if field not in fields]

    row_errors: list[str] = []
    numeric_values: dict[str, list[float]] = {field: [] for field in NUMERIC_FIELDS}
    quote_success_count = 0

    if not missing_fields:
        for index, row in enumerate(rows, start=1):
            if parse_bool(row.get("quote_ok")):
                quote_success_count += 1
            for field in NUMERIC_FIELDS:
                value = parse_float(row.get(field))
                if value is None:
                    row_errors.append(f"row {index}: missing_or_invalid {field}")
                    continue
                numeric_values[field].append(value)

    row_count = len(rows)
    coverage_pct = round((quote_success_count / row_count * 100.0), 3) if row_count else 0.0
    p50_total = percentile(numeric_values["total_latency_ms"], 0.50)
    p90_total = percentile(numeric_values["total_latency_ms"], 0.90)
    p50_quote = percentile(numeric_values["quote_latency_ms"], 0.50)
    p90_quote = percentile(numeric_values["quote_latency_ms"], 0.90)
    p50_detector = percentile(numeric_values["detector_latency_ms"], 0.50)
    p90_detector = percentile(numeric_values["detector_latency_ms"], 0.90)

    reasons: list[str] = []
    if missing_fields:
        reasons.append("missing required latency fields")
    if row_count == 0:
        reasons.append("no latency rows")
    if row_errors:
        reasons.append("missing or invalid timestamp/latency values")

    run_mode_normalized = str(run_mode).strip().lower()
    enough_live_rows = row_count >= min_live_rows
    metrics_filled = all(
        value is not None for value in (p50_total, p90_total, p50_quote, p90_quote, p50_detector, p90_detector)
    )

    if reasons:
        verdict = "FAIL"
    elif run_mode_normalized != "live" or not enough_live_rows:
        verdict = "SMOKE_ONLY"
        if run_mode_normalized != "live":
            reasons.append("run mode is not live")
        if not enough_live_rows:
            reasons.append(f"row count {row_count} below live minimum {min_live_rows}")
    elif (
        metrics_filled
        and coverage_pct >= coverage_target_pct
        and p50_total is not None
        and p90_total is not None
        and p50_total < p50_total_target_ms
        and p90_total < p90_total_target_ms
    ):
        verdict = "PASS"
    else:
        verdict = "FAIL"
        if coverage_pct < coverage_target_pct:
            reasons.append(f"coverage {coverage_pct:.3f}% below {coverage_target_pct:.3f}%")
        if p50_total is None or p50_total >= p50_total_target_ms:
            reasons.append("p50 total latency missing or above target")
        if p90_total is None or p90_total >= p90_total_target_ms:
            reasons.append("p90 total latency missing or above target")
        if not metrics_filled:
            reasons.append("quote/detector latency metrics missing")

    status = {
        "PASS": "ACTIVE / GATE PASSED",
        "FAIL": "ACTIVE / GATE FAILED",
        "SMOKE_ONLY": "SMOKE_ONLY",
    }[verdict]

    return {
        "verdict": verdict,
        "status": status,
        "run_mode": run_mode_normalized,
        "row_count": row_count,
        "min_live_rows": min_live_rows,
        "quote_success_count": quote_success_count,
        "coverage_pct": coverage_pct,
        "p50_total_latency_ms": round_metric(p50_total),
        "p90_total_latency_ms": round_metric(p90_total),
        "p50_quote_latency_ms": round_metric(p50_quote),
        "p90_quote_latency_ms": round_metric(p90_quote),
        "p50_detector_latency_ms": round_metric(p50_detector),
        "p90_detector_latency_ms": round_metric(p90_detector),
        "missing_fields": missing_fields,
        "row_errors": row_errors[:25],
        "reasons": reasons,
        "live_network_confirmed": run_mode_normalized == "live" and enough_live_rows and not missing_fields and not row_errors,
        "decision_boundary": "Paper mode remains blocked unless this verdict is PASS. Live execution remains forbidden.",
    }


def evaluate_file(path: Path, *, run_mode: str = "live", min_live_rows: int = 50) -> dict[str, Any]:
    if not path.exists():
        result = evaluate_rows([], fieldnames=[], run_mode=run_mode, min_live_rows=min_live_rows)
        result["reasons"].insert(0, f"input not found: {path}")
        return result
    rows, fieldnames = read_latency_csv(path)
    return evaluate_rows(rows, fieldnames=fieldnames, run_mode=run_mode, min_live_rows=min_live_rows)


def render_report(result: dict[str, Any], *, source_label: str) -> str:
    lines = [
        "# Observer Live-Run Gate Report",
        "",
        f"- Source: `{source_label}`",
        f"- Status: `{result['status']}`",
        f"- Verdict: `{result['verdict']}`",
        f"- Run mode: `{result['run_mode']}`",
        "- Safety: `monitoring only`, `NO_PRIVATE_KEYS`, `NO_SIGNING`, `NO_SWAP_SEND`",
        "",
    ]

    if result["verdict"] == "SMOKE_ONLY":
        lines.extend(
            [
                "Observer harness validated; live network run pending.",
                "",
            ]
        )

    lines.extend(
        [
            "## Metrics",
            "",
            "| Metric | Value |",
            "|---|---:|",
            f"| rows | `{result['row_count']}` |",
            f"| quote_success_count | `{result['quote_success_count']}` |",
            f"| coverage_pct | `{result['coverage_pct']}` |",
            f"| p50_total_latency_ms | `{result['p50_total_latency_ms']}` |",
            f"| p90_total_latency_ms | `{result['p90_total_latency_ms']}` |",
            f"| p50_quote_latency_ms | `{result['p50_quote_latency_ms']}` |",
            f"| p90_quote_latency_ms | `{result['p90_quote_latency_ms']}` |",
            f"| p50_detector_latency_ms | `{result['p50_detector_latency_ms']}` |",
            f"| p90_detector_latency_ms | `{result['p90_detector_latency_ms']}` |",
            "",
            "## Reasons",
            "",
        ]
    )

    reasons = result.get("reasons") or ["none"]
    lines.extend(f"- {reason}" for reason in reasons)
    if result.get("missing_fields"):
        lines.append(f"- missing_fields: `{', '.join(result['missing_fields'])}`")
    if result.get("row_errors"):
        lines.append(f"- row_errors_sample: `{'; '.join(result['row_errors'])}`")

    lines.extend(
        [
            "",
            "## Decision Boundary",
            "",
            "Paper mode is blocked unless Gate 2 returns `PASS` on a real network-enabled run.",
            "Live execution remains forbidden until a separate security review, private-key boundary, slippage replay, fail-safe, and explicit approval.",
        ]
    )
    return "\n".join(lines) + "\n"


def maybe_record_research_finding(result: dict[str, Any], *, run_key: str | None) -> dict[str, Any] | None:
    if not run_key:
        return None
    from repositories import ResearchRepo

    repo = ResearchRepo.from_env()
    return repo.record_observer_gate_verdict(run_key=run_key, gate_result=result)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate Observer latency gate from observer_latency_live.csv")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Path to observer_latency_live.csv")
    parser.add_argument("--report", default=str(DEFAULT_REPORT), help="Markdown report path")
    parser.add_argument("--json", default=str(DEFAULT_JSON), help="JSON result path")
    parser.add_argument("--run-mode", choices=["live", "smoke"], default="live")
    parser.add_argument("--min-live-rows", type=int, default=50)
    parser.add_argument(
        "--research-run-key",
        default=None,
        help="Optional run_key. If set, writes the gate verdict into research_runs/research_findings.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    result = evaluate_file(input_path, run_mode=args.run_mode, min_live_rows=args.min_live_rows)
    research_record = maybe_record_research_finding(result, run_key=args.research_run_key)
    if research_record is not None:
        result["research_record"] = research_record
    report = render_report(result, source_label=str(input_path))

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")

    json_path = Path(args.json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print(report)
    if research_record is not None:
        print(json.dumps({"research_record": research_record}, indent=2, ensure_ascii=False, default=str))
    if result["verdict"] == "PASS":
        return 0
    if result["verdict"] == "SMOKE_ONLY":
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

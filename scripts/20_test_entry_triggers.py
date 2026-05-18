#!/usr/bin/env python3
"""Test whether pre-buy entry context separates from matched controls.

M3.2 guardrails:
- data-quality features are separated from trading-trigger features;
- constant / zero-variance features cannot become PASS;
- precision@k is tie-aware and does not reward arbitrary ordering;
- coverage is distinct from information content.

The script writes:
- data/processed/trigger_tests.csv
- reports/prebuy_trigger_report.md
"""

from __future__ import annotations

import argparse
import math
import random
from pathlib import Path
from statistics import median
from typing import Any

from common import DATA_PROCESSED, REPORTS, ensure_dirs, read_csv, write_csv

UNKNOWN = "UNKNOWN"
DEFAULT_BOOTSTRAP_ITERS = 300
DEFAULT_TOP_K = 10
EPS = 1e-12

TEST_FIELDNAMES = [
    "test_id",
    "test_scope",
    "feature_id",
    "family",
    "source",
    "feature_role",
    "direction",
    "n_entry",
    "n_control",
    "coverage_pct",
    "nonzero_rate_entry",
    "nonzero_rate_control",
    "variance_entry",
    "variance_control",
    "unique_values_count",
    "information_status",
    "median_entry",
    "median_control",
    "mean_entry",
    "mean_control",
    "effect_size",
    "cliffs_delta",
    "bootstrap_ci_low",
    "bootstrap_ci_high",
    "auc",
    "precision_at_k",
    "baseline_precision",
    "verdict",
    "status_reason",
    "notes",
]

DEFAULT_FEATURES = [
    {"feature_id": "wallet_buy_count_30s", "family": "wallet_flow", "source": "wallet_swaps", "direction": "higher", "feature_role": "trading_trigger"},
    {"feature_id": "wallet_sell_count_30s", "family": "wallet_flow", "source": "wallet_swaps", "direction": "lower", "feature_role": "trading_trigger"},
    {"feature_id": "wallet_net_buy_sol_30s", "family": "wallet_flow", "source": "wallet_swaps", "direction": "higher", "feature_role": "trading_trigger"},
    {"feature_id": "wallet_volume_sol_30s", "family": "wallet_flow", "source": "wallet_swaps", "direction": "higher", "feature_role": "trading_trigger"},
    {"feature_id": "wallet_tx_count_30s", "family": "wallet_flow", "source": "wallet_swaps", "direction": "higher", "feature_role": "trading_trigger"},
    {"feature_id": "price_return_30s", "family": "price_action", "source": "price_series", "direction": "higher", "feature_role": "trading_trigger"},
    {"feature_id": "same_wallet_prior_entries_count", "family": "repeat_wave", "source": "trades_paired;wallet_swaps", "direction": "higher", "feature_role": "trading_trigger"},
    {"feature_id": "same_wallet_prior_pnl_sol", "family": "repeat_wave", "source": "trades_paired", "direction": "higher", "feature_role": "trading_trigger"},
    {"feature_id": "feature_coverage_pct", "family": "data_quality", "source": "entry_context", "direction": "higher", "feature_role": "data_quality"},
]


def is_known(value: Any) -> bool:
    return value not in (None, "", UNKNOWN)


def as_float_or_none(value: Any) -> float | None:
    if not is_known(value):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def transform_direction(values: list[float], direction: str) -> list[float]:
    return [-v for v in values] if direction == "lower" else values


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def variance(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = mean(values)
    return sum((x - m) ** 2 for x in values) / (len(values) - 1)


def stddev(values: list[float]) -> float:
    return math.sqrt(variance(values))


def nonzero_rate(values: list[float]) -> float:
    return sum(1 for value in values if abs(value) > EPS) / len(values) if values else 0.0


def unique_count(values: list[float]) -> int:
    return len({round(value, 12) for value in values})


def information_status(xs: list[float], ys: list[float], coverage: float) -> tuple[str, str]:
    combined = xs + ys
    if coverage <= 0 or not combined:
        return "EMPTY", "no_known_values"
    uniques = unique_count(combined)
    if uniques <= 1:
        return "CONSTANT", "constant_feature"
    vx = variance(xs)
    vy = variance(ys)
    if vx <= EPS and vy <= EPS:
        return "CONSTANT", "zero_variance_both_groups"
    if coverage < 70:
        return "LOW_COVERAGE", "low_coverage"
    return "VARIABLE", "variable_feature"


def pooled_effect_size(xs: list[float], ys: list[float]) -> float:
    if not xs or not ys:
        return 0.0
    nx, ny = len(xs), len(ys)
    sx, sy = stddev(xs), stddev(ys)
    dof = nx + ny - 2
    if dof > 0:
        pooled = math.sqrt(((nx - 1) * sx * sx + (ny - 1) * sy * sy) / dof)
    else:
        pooled = math.sqrt((sx * sx + sy * sy) / 2)
    if pooled <= EPS:
        return 0.0
    return (mean(xs) - mean(ys)) / pooled


def cliffs_delta(xs: list[float], ys: list[float]) -> float:
    if not xs or not ys:
        return 0.0
    greater = 0
    lower = 0
    for x in xs:
        for y in ys:
            if x > y:
                greater += 1
            elif x < y:
                lower += 1
    return (greater - lower) / (len(xs) * len(ys))


def bootstrap_median_diff(xs: list[float], ys: list[float], iters: int = DEFAULT_BOOTSTRAP_ITERS, seed: int = 17) -> tuple[float, float]:
    if not xs or not ys:
        return 0.0, 0.0
    rng = random.Random(seed)
    diffs: list[float] = []
    for _ in range(iters):
        sx = [xs[rng.randrange(len(xs))] for _ in xs]
        sy = [ys[rng.randrange(len(ys))] for _ in ys]
        diffs.append(float(median(sx) - median(sy)))
    diffs.sort()
    return diffs[int(0.025 * (len(diffs) - 1))], diffs[int(0.975 * (len(diffs) - 1))]


def tie_aware_precision_at_k(xs: list[float], ys: list[float], k: int = DEFAULT_TOP_K) -> tuple[float, float]:
    """Expected precision@k under random ordering inside score ties."""
    labeled = [(value, 1) for value in xs] + [(value, 0) for value in ys]
    if not labeled:
        return 0.0, 0.0
    baseline = len(xs) / len(labeled)
    if unique_count([value for value, _label in labeled]) <= 1:
        return baseline, baseline

    k_eff = min(k, len(labeled))
    labeled.sort(key=lambda item: item[0], reverse=True)
    cutoff = labeled[k_eff - 1][0]
    above = [(value, label) for value, label in labeled if value > cutoff]
    tied = [(value, label) for value, label in labeled if value == cutoff]
    slots_from_tie = k_eff - len(above)
    positives = sum(label for _value, label in above)
    if tied and slots_from_tie > 0:
        positives += sum(label for _value, label in tied) * (slots_from_tie / len(tied))
    return positives / k_eff, baseline


def verdict_for(
    *,
    feature_role: str,
    coverage: float,
    effect: float,
    delta: float,
    ci_low: float,
    ci_high: float,
    auc: float,
    precision: float,
    baseline: float,
    info_status: str,
    info_reason: str,
) -> tuple[str, str]:
    if info_status == "EMPTY":
        return "UNKNOWN", info_reason
    if info_status == "CONSTANT":
        return "NO_SIGNAL", info_reason
    if coverage < 70:
        return "UNKNOWN", "low_coverage"

    ci_positive = ci_low > 0 and ci_high > 0
    strong = coverage >= 80 and delta >= 0.33 and auc >= 0.62 and precision >= max(baseline * 1.5, baseline + 0.10)
    partial = ci_positive and effect >= 0.2 and delta > 0

    if feature_role == "data_quality":
        if strong:
            return "DATA_QUALITY_PASS", "data_quality_not_trading_trigger"
        if partial:
            return "DATA_QUALITY_PARTIAL", "data_quality_not_trading_trigger"
        return "DATA_QUALITY_NO_SIGNAL", "data_quality_not_trading_trigger"

    if strong:
        return "PASS", "entry_control_separation"
    if partial:
        return "PARTIAL", "weak_entry_control_separation"
    if effect <= -0.2 or delta < -0.1:
        return "FAIL", "opposite_direction_or_negative_effect"
    return "NO_SIGNAL", "insufficient_separation"


def collect_values(rows: list[dict[str, str]], feature_id: str) -> list[float]:
    return [value for row in rows if (value := as_float_or_none(row.get(feature_id))) is not None]


def feature_known_count(rows: list[dict[str, str]], feature_id: str) -> int:
    return sum(1 for row in rows if as_float_or_none(row.get(feature_id)) is not None)


def build_test_row(
    test_id: int,
    test_scope: str,
    feature: dict[str, str],
    group_a_rows: list[dict[str, str]],
    group_b_rows: list[dict[str, str]],
    group_a_name: str,
    group_b_name: str,
    bootstrap_iters: int,
    top_k: int,
) -> dict[str, Any]:
    feature_id = feature["feature_id"]
    family = feature.get("family", "unknown")
    direction = feature.get("direction", "higher")
    feature_role = feature.get("feature_role") or feature.get("role") or ("data_quality" if family == "data_quality" else "trading_trigger")

    raw_xs = collect_values(group_a_rows, feature_id)
    raw_ys = collect_values(group_b_rows, feature_id)
    xs = transform_direction(raw_xs, direction)
    ys = transform_direction(raw_ys, direction)

    total = len(group_a_rows) + len(group_b_rows)
    known_total = feature_known_count(group_a_rows, feature_id) + feature_known_count(group_b_rows, feature_id)
    coverage = (known_total / total * 100) if total else 0.0
    info_status, info_reason = information_status(xs, ys, coverage)

    effect = pooled_effect_size(xs, ys) if info_status == "VARIABLE" else 0.0
    delta = cliffs_delta(xs, ys) if info_status == "VARIABLE" else 0.0
    ci_low, ci_high = bootstrap_median_diff(xs, ys, bootstrap_iters) if info_status == "VARIABLE" else (0.0, 0.0)
    auc = (delta + 1) / 2 if info_status == "VARIABLE" else 0.5
    precision, baseline = tie_aware_precision_at_k(xs, ys, top_k)
    verdict, status_reason = verdict_for(
        feature_role=feature_role,
        coverage=coverage,
        effect=effect,
        delta=delta,
        ci_low=ci_low,
        ci_high=ci_high,
        auc=auc,
        precision=precision,
        baseline=baseline,
        info_status=info_status,
        info_reason=info_reason,
    )

    return {
        "test_id": test_id,
        "test_scope": test_scope,
        "feature_id": feature_id,
        "family": family,
        "source": feature.get("source", "unknown"),
        "feature_role": feature_role,
        "direction": direction,
        "n_entry": len(raw_xs),
        "n_control": len(raw_ys),
        "coverage_pct": f"{coverage:.2f}",
        "nonzero_rate_entry": f"{nonzero_rate(raw_xs):.6f}",
        "nonzero_rate_control": f"{nonzero_rate(raw_ys):.6f}",
        "variance_entry": f"{variance(raw_xs):.12f}",
        "variance_control": f"{variance(raw_ys):.12f}",
        "unique_values_count": unique_count(xs + ys),
        "information_status": info_status,
        "median_entry": f"{median(raw_xs):.8f}" if raw_xs else "",
        "median_control": f"{median(raw_ys):.8f}" if raw_ys else "",
        "mean_entry": f"{mean(raw_xs):.8f}" if raw_xs else "",
        "mean_control": f"{mean(raw_ys):.8f}" if raw_ys else "",
        "effect_size": f"{effect:.6f}",
        "cliffs_delta": f"{delta:.6f}",
        "bootstrap_ci_low": f"{ci_low:.8f}",
        "bootstrap_ci_high": f"{ci_high:.8f}",
        "auc": f"{auc:.6f}",
        "precision_at_k": f"{precision:.6f}",
        "baseline_precision": f"{baseline:.6f}",
        "verdict": verdict,
        "status_reason": status_reason,
        "notes": f"{group_a_name} vs {group_b_name}; direction-normalized stats; {info_reason}",
    }


def strip_scalar(value: str) -> str:
    return value.strip().strip("\"'")


def load_manifest(path: Path | None) -> list[dict[str, str]]:
    if path is None or not path.exists():
        return DEFAULT_FEATURES
    features: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped.startswith("features:"):
            continue
        if stripped.startswith("-"):
            if current:
                features.append(current)
            current = {}
            rest = stripped[1:].strip()
            if rest and ":" in rest:
                key, value = rest.split(":", 1)
                current[key.strip()] = strip_scalar(value)
            continue
        if current is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            current[key.strip()] = strip_scalar(value)
    if current:
        features.append(current)
    cleaned = [feature for feature in features if feature.get("feature_id")]
    return cleaned or DEFAULT_FEATURES


def build_trigger_tests(
    entry_rows: list[dict[str, str]],
    control_rows: list[dict[str, str]],
    features: list[dict[str, str]],
    bootstrap_iters: int = DEFAULT_BOOTSTRAP_ITERS,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []
    test_id = 0
    for feature in features:
        test_id += 1
        tests.append(build_test_row(test_id, "entry_vs_control", feature, entry_rows, control_rows, "entry", "control", bootstrap_iters, top_k))

    winners = [row for row in entry_rows if str(row.get("sample_class", "")).lower() == "winner" or str(row.get("label_win", "")).lower() == "true" or str(row.get("outcome_win", "")).lower() == "true"]
    losers = [row for row in entry_rows if str(row.get("sample_class", "")).lower() == "loser" or str(row.get("label_win", "")).lower() == "false" or str(row.get("outcome_win", "")).lower() == "false"]
    if winners and losers:
        for feature in features:
            test_id += 1
            tests.append(build_test_row(test_id, "winner_vs_loser", feature, winners, losers, "winner", "loser", bootstrap_iters, top_k))
    return tests


def render_report(rows: list[dict[str, Any]], entry_count: int, control_count: int) -> str:
    verdict_counts: dict[str, int] = {}
    role_counts: dict[str, int] = {}
    info_counts: dict[str, int] = {}
    for row in rows:
        verdict = str(row.get("verdict", "UNKNOWN"))
        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
        role = str(row.get("feature_role", "unknown"))
        role_counts[role] = role_counts.get(role, 0) + 1
        info = str(row.get("information_status", "UNKNOWN"))
        info_counts[info] = info_counts.get(info, 0) + 1

    lines = [
        "# Pre-buy Trigger Test Report",
        "",
        "## Summary",
        "",
        f"- Entry rows: `{entry_count}`",
        f"- Control rows: `{control_count}`",
        f"- Trigger tests: `{len(rows)}`",
        "- Guardrail: `DATA_QUALITY_*` verdicts are not trading triggers.",
        "- Guardrail: constant / zero-variance features cannot become PASS.",
        "- Guardrail: this report does not prove H4 without sufficient coverage, controls, and out-of-sample validation.",
        "",
        "## Verdict counts",
        "",
    ]
    for verdict in sorted(verdict_counts):
        lines.append(f"- `{verdict}`: `{verdict_counts[verdict]}`")
    lines.extend(["", "## Feature role counts", ""])
    for role in sorted(role_counts):
        lines.append(f"- `{role}`: `{role_counts[role]}`")
    lines.extend(["", "## Information status counts", ""])
    for info in sorted(info_counts):
        lines.append(f"- `{info}`: `{info_counts[info]}`")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Test pre-buy trigger separation")
    parser.add_argument("--entry-context", default=str(DATA_PROCESSED / "entry_context.csv"))
    parser.add_argument("--control-points", default=str(DATA_PROCESSED / "control_points.csv"))
    parser.add_argument("--manifest", default="configs/prebuy_feature_manifest.yaml")
    parser.add_argument("--output", default=str(DATA_PROCESSED / "trigger_tests.csv"))
    parser.add_argument("--report", default=str(REPORTS / "prebuy_trigger_report.md"))
    parser.add_argument("--bootstrap-iters", type=int, default=DEFAULT_BOOTSTRAP_ITERS)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    args = parser.parse_args()

    ensure_dirs()
    entry_rows = read_csv(Path(args.entry_context))
    control_rows = read_csv(Path(args.control_points))
    features = load_manifest(Path(args.manifest) if args.manifest else None)
    rows = build_trigger_tests(entry_rows, control_rows, features, args.bootstrap_iters, args.top_k)
    write_csv(Path(args.output), rows, TEST_FIELDNAMES)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(rows, len(entry_rows), len(control_rows)), encoding="utf-8")
    print(f"[OK] wrote {len(rows)} trigger tests to {args.output}")


if __name__ == "__main__":
    main()

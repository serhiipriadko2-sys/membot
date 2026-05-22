#!/usr/bin/env python3
"""Validate precomputed Dune aggregate entry/control context.

This adapter is for Dune exports that already contain anchor-level aggregate
features, not raw `dex_solana.trades` rows. It keeps that provenance explicit so
aggregate context is not confused with wallet accounting or raw market trades.
"""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path
from typing import Any

from common import DATA_PROCESSED, REPORTS, ensure_dirs, read_csv, write_csv

trigger_tests = importlib.import_module("20_test_entry_triggers")

DEFAULT_DUNE_AGGREGATE_FEATURES = [
    {
        "feature_id": "trade_count_300s",
        "family": "dune_market_activity",
        "source": "dune_aggregate_context",
        "direction": "higher",
        "feature_role": "research_signal",
    },
    {
        "feature_id": "volume_usd_300s",
        "family": "dune_market_volume",
        "source": "dune_aggregate_context",
        "direction": "higher",
        "feature_role": "research_signal",
    },
    {
        "feature_id": "volume_usd_30s",
        "family": "dune_market_volume",
        "source": "dune_aggregate_context",
        "direction": "higher",
        "feature_role": "research_signal",
    },
    {
        "feature_id": "volume_accel_60_300",
        "family": "dune_crescendo",
        "source": "dune_aggregate_context",
        "direction": "higher",
        "feature_role": "research_signal",
    },
    {
        "feature_id": "volume_accel_30_300",
        "family": "dune_crescendo",
        "source": "dune_aggregate_context",
        "direction": "higher",
        "feature_role": "research_signal",
    },
    {
        "feature_id": "volume_accel_10_300",
        "family": "dune_crescendo",
        "source": "dune_aggregate_context",
        "direction": "higher",
        "feature_role": "research_signal",
    },
    {
        "feature_id": "buy_pressure_300s",
        "family": "dune_buy_pressure",
        "source": "dune_aggregate_context",
        "direction": "higher",
        "feature_role": "research_signal",
    },
    {
        "feature_id": "crescendo_broad_30_p80",
        "family": "dune_crescendo",
        "source": "dune_aggregate_context",
        "direction": "higher",
        "feature_role": "research_signal",
    },
    {
        "feature_id": "crescendo_strict_30_p90",
        "family": "dune_crescendo",
        "source": "dune_aggregate_context",
        "direction": "higher",
        "feature_role": "research_signal",
    },
    {
        "feature_id": "crescendo_fast_10_p90",
        "family": "dune_crescendo",
        "source": "dune_aggregate_context",
        "direction": "higher",
        "feature_role": "research_signal",
    },
    {
        "feature_id": "crescendo_or_30p90_10p90",
        "family": "dune_crescendo",
        "source": "dune_aggregate_context",
        "direction": "higher",
        "feature_role": "research_signal",
    },
    {
        "feature_id": "crescendo_plus_buy_pressure",
        "family": "dune_crescendo",
        "source": "dune_aggregate_context",
        "direction": "higher",
        "feature_role": "research_signal",
    },
]


def split_dune_aggregate_context(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    entries = [row for row in rows if row.get("anchor_type") == "entry"]
    controls = [row for row in rows if row.get("anchor_type") != "entry"]
    return entries, controls


def summarize_source_rows(rows: list[dict[str, str]]) -> dict[str, int]:
    grouped: dict[str, dict[str, int]] = {}
    for row in rows:
        source_id = row.get("source_row_id") or row.get("anchor_id") or ""
        if not source_id:
            continue
        group = grouped.setdefault(source_id, {"entry": 0, "control": 0})
        if row.get("anchor_type") == "entry":
            group["entry"] += 1
        else:
            group["control"] += 1
    return {
        "source_row_ids": len(grouped),
        "complete_1_entry_3_control_groups": sum(
            1 for group in grouped.values() if group["entry"] == 1 and group["control"] == 3
        ),
        "groups_without_one_entry": sum(1 for group in grouped.values() if group["entry"] != 1),
        "groups_without_three_controls": sum(1 for group in grouped.values() if group["control"] != 3),
    }


def build_dune_aggregate_trigger_tests(
    rows: list[dict[str, str]],
    features: list[dict[str, str]] | None = None,
    bootstrap_iters: int = 300,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    entry_rows, control_rows = split_dune_aggregate_context(rows)
    return trigger_tests.build_trigger_tests(
        entry_rows=entry_rows,
        control_rows=control_rows,
        features=features or DEFAULT_DUNE_AGGREGATE_FEATURES,
        bootstrap_iters=bootstrap_iters,
        top_k=top_k,
    )


def render_dune_aggregate_report(
    rows: list[dict[str, Any]],
    entry_count: int,
    control_count: int,
    source_summary: dict[str, int],
) -> str:
    base = trigger_tests.render_report(rows, entry_count, control_count)
    total_groups = source_summary.get("source_row_ids", 0)
    complete_groups = source_summary.get("complete_1_entry_3_control_groups", 0)
    return (
        base
        + "\n## Dune aggregate guardrail\n\n"
        + "This report validates precomputed Dune anchor features only. It is not a trading signal, "
        + "not raw wallet accounting, and not final proof of a trigger until the canonical raw/FIFO, "
        + "fee, latency, slippage, and out-of-sample checks pass.\n\n"
        + "## Source row grouping\n\n"
        + f"- source row ids: `{total_groups}`\n"
        + f"- complete 1-entry / 3-control groups: `{complete_groups} / {total_groups}`\n"
        + f"- groups without exactly one entry: `{source_summary.get('groups_without_one_entry', 0)}`\n"
        + f"- groups without exactly three controls: `{source_summary.get('groups_without_three_controls', 0)}`\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Test precomputed Dune aggregate entry/control context")
    parser.add_argument("--input", default="result.csv", help="Dune aggregate CSV export")
    parser.add_argument("--output", default=str(DATA_PROCESSED / "dune_aggregate_trigger_tests.csv"))
    parser.add_argument("--report", default=str(REPORTS / "dune_aggregate_trigger_report.md"))
    parser.add_argument("--bootstrap-iters", type=int, default=300)
    parser.add_argument("--top-k", type=int, default=10)
    args = parser.parse_args()

    ensure_dirs()
    rows = read_csv(Path(args.input))
    entry_rows, control_rows = split_dune_aggregate_context(rows)
    tests = build_dune_aggregate_trigger_tests(rows, bootstrap_iters=args.bootstrap_iters, top_k=args.top_k)
    write_csv(Path(args.output), tests, trigger_tests.TEST_FIELDNAMES)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        render_dune_aggregate_report(tests, len(entry_rows), len(control_rows), summarize_source_rows(rows)),
        encoding="utf-8",
    )
    print(f"[OK] wrote {len(tests)} Dune aggregate trigger tests to {args.output}")


if __name__ == "__main__":
    main()

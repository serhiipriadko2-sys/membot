#!/usr/bin/env python3
"""Validate cluster context against matched control points.

Cluster presence is not alpha. This script tests whether cluster-context features
separate real entry anchors from matched control anchors. If they do not, H4
cluster claims remain UNKNOWN/NO_SIGNAL.
"""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path
from typing import Any

from common import DATA_PROCESSED, REPORTS, ensure_dirs, read_csv, write_csv

cluster_builder = importlib.import_module("21_build_cluster_context")
trigger_tests = importlib.import_module("20_test_entry_triggers")

DEFAULT_CLUSTER_FEATURES = [
    {"feature_id": "cluster_presence_score", "family": "cluster", "source": "wallet_swaps", "direction": "higher"},
    {"feature_id": "cluster_quality_score", "family": "cluster", "source": "wallet_swaps", "direction": "higher"},
    {"feature_id": "cluster_toxicity_score", "family": "cluster", "source": "wallet_swaps", "direction": "lower"},
    {"feature_id": "cluster_lead_time_score", "family": "cluster", "source": "wallet_swaps", "direction": "higher"},
    {"feature_id": "cluster_exit_pressure_score", "family": "cluster", "source": "wallet_swaps", "direction": "lower"},
    {"feature_id": "funding_source_similarity", "family": "cluster", "source": "wallet_swaps", "direction": "lower"},
    {"feature_id": "position_size_similarity", "family": "cluster", "source": "wallet_swaps", "direction": "lower"},
    {"feature_id": "route_similarity", "family": "cluster", "source": "wallet_swaps", "direction": "lower"},
]


def controls_to_anchor_entries(control_points: list[dict[str, str]]) -> list[dict[str, str]]:
    anchors: list[dict[str, str]] = []
    for control in control_points:
        control_time = control.get("control_time")
        if not control_time:
            continue
        anchors.append({
            "entry_signature": f"control:{control.get('control_id', '')}:{control.get('entry_signature', '')}",
            "token_mint": control.get("token_mint", ""),
            "entry_time": control_time,
            "entry_slot": control.get("control_slot", "0") or "0",
            "sample_class": "control",
        })
    return anchors


def build_cluster_trigger_tests(
    entry_context: list[dict[str, str]],
    control_points: list[dict[str, str]],
    swaps: list[dict[str, str]],
    window: int = 300,
    min_wallets: int = 3,
    bootstrap_iters: int = 300,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    entry_rows = cluster_builder.build_cluster_context(entry_context, swaps, window=window, min_wallets=min_wallets)
    control_rows = cluster_builder.build_cluster_context(controls_to_anchor_entries(control_points), swaps, window=window, min_wallets=min_wallets)
    return trigger_tests.build_trigger_tests(
        entry_rows=entry_rows,
        control_rows=control_rows,
        features=DEFAULT_CLUSTER_FEATURES,
        bootstrap_iters=bootstrap_iters,
        top_k=top_k,
    )


def render_cluster_report(rows: list[dict[str, Any]], entry_count: int, control_count: int) -> str:
    base = trigger_tests.render_report(rows, entry_count, control_count)
    return base + "\n## Cluster guardrail\n\nCluster presence is context only. A PASS requires later OOS and latency/slippage checks before any edge claim.\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Test cluster context against matched controls")
    parser.add_argument("--entry-context", default=str(DATA_PROCESSED / "entry_context.csv"))
    parser.add_argument("--control-points", default=str(DATA_PROCESSED / "control_points.csv"))
    parser.add_argument("--swaps", default=str(DATA_PROCESSED / "wallet_swaps.csv"))
    parser.add_argument("--output", default=str(DATA_PROCESSED / "cluster_trigger_tests.csv"))
    parser.add_argument("--report", default=str(REPORTS / "cluster_trigger_report.md"))
    parser.add_argument("--window-seconds", type=int, default=300)
    parser.add_argument("--min-wallets", type=int, default=3)
    parser.add_argument("--bootstrap-iters", type=int, default=300)
    parser.add_argument("--top-k", type=int, default=10)
    args = parser.parse_args()

    ensure_dirs()
    entry_context = read_csv(Path(args.entry_context))
    control_points = read_csv(Path(args.control_points))
    rows = build_cluster_trigger_tests(
        entry_context=entry_context,
        control_points=control_points,
        swaps=read_csv(Path(args.swaps)),
        window=args.window_seconds,
        min_wallets=args.min_wallets,
        bootstrap_iters=args.bootstrap_iters,
        top_k=args.top_k,
    )
    write_csv(Path(args.output), rows, trigger_tests.TEST_FIELDNAMES)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_cluster_report(rows, len(entry_context), len(control_points)), encoding="utf-8")
    print(f"[OK] wrote {len(rows)} cluster trigger tests to {args.output}")


if __name__ == "__main__":
    main()

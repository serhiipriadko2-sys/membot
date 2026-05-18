#!/usr/bin/env python3
"""Validate cross-chain regime context against matched controls.

Cross-chain context is a regime filter, not token-specific BUY proof. This script
compares pre-entry cross-chain context against matched control anchors and keeps
missing coverage as UNKNOWN.
"""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path
from typing import Any

from common import DATA_PROCESSED, REPORTS, ensure_dirs, read_csv, write_csv

cross_builder = importlib.import_module("22_build_cross_chain_context")
trigger_tests = importlib.import_module("20_test_entry_triggers")
cluster_tests = importlib.import_module("23_test_cluster_triggers")

DEFAULT_CROSS_CHAIN_FEATURES = [
    {"feature_id": "combined_momentum", "family": "cross_chain_regime", "source": "cross_chain_events", "direction": "higher"},
    {"feature_id": "signal_count", "family": "cross_chain_regime", "source": "cross_chain_events", "direction": "higher"},
    {"feature_id": "bridge_inflow_usd_15m", "family": "cross_chain_regime", "source": "cross_chain_events", "direction": "higher"},
    {"feature_id": "bridge_outflow_usd_15m", "family": "cross_chain_regime", "source": "cross_chain_events", "direction": "lower"},
    {"feature_id": "cross_chain_attention_delta", "family": "cross_chain_regime", "source": "cross_chain_events", "direction": "higher"},
]


def build_cross_chain_trigger_tests(
    entry_context: list[dict[str, str]],
    control_points: list[dict[str, str]],
    events: list[dict[str, str]],
    window: int = 900,
    bootstrap_iters: int = 300,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    entry_rows = cross_builder.build_cross_chain_context(entry_context, events, window=window)
    control_rows = cross_builder.build_cross_chain_context(cluster_tests.controls_to_anchor_entries(control_points), events, window=window)
    return trigger_tests.build_trigger_tests(
        entry_rows=entry_rows,
        control_rows=control_rows,
        features=DEFAULT_CROSS_CHAIN_FEATURES,
        bootstrap_iters=bootstrap_iters,
        top_k=top_k,
    )


def render_cross_chain_report(rows: list[dict[str, Any]], entry_count: int, control_count: int) -> str:
    base = trigger_tests.render_report(rows, entry_count, control_count)
    return base + "\n## Cross-chain guardrail\n\nCross-chain PASS means regime separation under current local events only. It is not token-specific BUY evidence.\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Test cross-chain regime context against matched controls")
    parser.add_argument("--entry-context", default=str(DATA_PROCESSED / "entry_context.csv"))
    parser.add_argument("--control-points", default=str(DATA_PROCESSED / "control_points.csv"))
    parser.add_argument("--events", default=str(DATA_PROCESSED / "cross_chain_events.csv"))
    parser.add_argument("--output", default=str(DATA_PROCESSED / "cross_chain_trigger_tests.csv"))
    parser.add_argument("--report", default=str(REPORTS / "cross_chain_trigger_report.md"))
    parser.add_argument("--window-seconds", type=int, default=900)
    parser.add_argument("--bootstrap-iters", type=int, default=300)
    parser.add_argument("--top-k", type=int, default=10)
    args = parser.parse_args()

    ensure_dirs()
    entry_context = read_csv(Path(args.entry_context))
    control_points = read_csv(Path(args.control_points))
    rows = build_cross_chain_trigger_tests(
        entry_context=entry_context,
        control_points=control_points,
        events=read_csv(Path(args.events)),
        window=args.window_seconds,
        bootstrap_iters=args.bootstrap_iters,
        top_k=args.top_k,
    )
    write_csv(Path(args.output), rows, trigger_tests.TEST_FIELDNAMES)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_cross_chain_report(rows, len(entry_context), len(control_points)), encoding="utf-8")
    print(f"[OK] wrote {len(rows)} cross-chain trigger tests to {args.output}")


if __name__ == "__main__":
    main()

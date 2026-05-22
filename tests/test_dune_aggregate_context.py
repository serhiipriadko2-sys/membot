from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

dune_aggregate = import_module("33_test_dune_aggregate_context")


def test_source_row_summary_counts_entry_control_groups() -> None:
    rows = [
        {"source_row_id": "1", "anchor_type": "entry"},
        {"source_row_id": "1", "anchor_type": "control"},
        {"source_row_id": "1", "anchor_type": "control"},
        {"source_row_id": "1", "anchor_type": "control"},
        {"source_row_id": "2", "anchor_type": "entry"},
        {"source_row_id": "2", "anchor_type": "control"},
    ]

    summary = dune_aggregate.summarize_source_rows(rows)

    assert summary["source_row_ids"] == 2
    assert summary["complete_1_entry_3_control_groups"] == 1
    assert summary["groups_without_one_entry"] == 0
    assert summary["groups_without_three_controls"] == 1


def test_dune_aggregate_trigger_tests_use_native_columns() -> None:
    rows = [
        {
            "source_row_id": "1",
            "anchor_type": "entry",
            "trade_count_300s": "30",
            "volume_accel_60_300": "0.80",
            "crescendo_broad_30_p80": "1",
        },
        {
            "source_row_id": "2",
            "anchor_type": "entry",
            "trade_count_300s": "40",
            "volume_accel_60_300": "0.90",
            "crescendo_broad_30_p80": "1",
        },
        {
            "source_row_id": "1",
            "anchor_type": "control",
            "trade_count_300s": "3",
            "volume_accel_60_300": "0.10",
            "crescendo_broad_30_p80": "0",
        },
        {
            "source_row_id": "2",
            "anchor_type": "control",
            "trade_count_300s": "4",
            "volume_accel_60_300": "0.20",
            "crescendo_broad_30_p80": "0",
        },
    ]

    tests = dune_aggregate.build_dune_aggregate_trigger_tests(rows, bootstrap_iters=20, top_k=2)

    assert tests
    assert {row["test_scope"] for row in tests} == {"entry_vs_control"}
    assert any(row["feature_id"] == "volume_accel_60_300" for row in tests)
    assert any(row["feature_id"] == "crescendo_broad_30_p80" for row in tests)
    accel = next(row for row in tests if row["feature_id"] == "volume_accel_60_300")
    assert accel["n_entry"] == 2
    assert accel["n_control"] == 2
    assert float(accel["cliffs_delta"]) > 0


def test_dune_aggregate_report_contains_guardrail_and_group_summary() -> None:
    summary = {
        "source_row_ids": 2,
        "complete_1_entry_3_control_groups": 1,
        "groups_without_one_entry": 0,
        "groups_without_three_controls": 1,
    }

    report = dune_aggregate.render_dune_aggregate_report([], entry_count=2, control_count=4, source_summary=summary)

    assert "Dune aggregate guardrail" in report
    assert "not a trading signal" in report
    assert "complete 1-entry / 3-control groups: `1 / 2`" in report

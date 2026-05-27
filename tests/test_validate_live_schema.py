from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import validate_live_schema as schema  # noqa: E402


class _Response:
    def __init__(self, data, count=0) -> None:
        self.data = data
        self.count = count


class _TableOp:
    def __init__(self, table_name: str, missing: set[str]) -> None:
        self.table_name = table_name
        self.missing = missing

    def select(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def execute(self):
        if self.table_name in self.missing:
            raise RuntimeError("relation does not exist")
        columns = schema.EXPECTED_COLUMNS.get(self.table_name, set())
        return _Response([{column: None for column in columns}], count=1)


class _FakeClient:
    def __init__(self, missing=None) -> None:
        self.missing = set(missing or [])

    def table(self, table_name: str) -> _TableOp:
        return _TableOp(table_name, self.missing)


def test_probe_table_passes_when_expected_columns_are_present() -> None:
    result = schema.probe_table(_FakeClient(), "research_findings")

    assert result["exists"] is True
    assert result["column_status"] == "PASS"
    assert result["missing_columns"] == []


def test_probe_table_fails_when_table_is_missing() -> None:
    result = schema.probe_table(_FakeClient(missing={"research_runs"}), "research_runs")

    assert result["exists"] is False
    assert result["column_status"] == "FAIL"


def test_rejected_drift_tables_are_named() -> None:
    assert schema.REJECTED_DRIFT_TABLES == {"hypotheses", "events", "evidence_log"}

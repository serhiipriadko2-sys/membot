from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from repositories.research_repo import ResearchRepo  # noqa: E402


class _TableOp:
    def __init__(self, table_name: str, client: "_FakeClient") -> None:
        self.table_name = table_name
        self.client = client
        self.payload = None
        self.conflict = None

    def upsert(self, payload, on_conflict=None):
        self.payload = payload
        self.conflict = on_conflict
        return self

    def execute(self):
        self.client.calls.append(
            {"table": self.table_name, "payload": self.payload, "on_conflict": self.conflict}
        )
        return type("Response", (), {"data": [self.payload]})()


class _FakeClient:
    def __init__(self) -> None:
        self.calls = []

    def table(self, table_name: str) -> _TableOp:
        return _TableOp(table_name, self)


def test_upsert_finding_validates_truth_label() -> None:
    repo = ResearchRepo(_FakeClient())

    with pytest.raises(ValueError):
        repo.upsert_finding(
            run_key="run",
            finding_key="finding",
            truth_label="WRONG",
            verdict="FAIL",
            confidence=0.5,
        )


def test_upsert_finding_validates_confidence_range() -> None:
    repo = ResearchRepo(_FakeClient())

    with pytest.raises(ValueError):
        repo.upsert_finding(
            run_key="run",
            finding_key="finding",
            truth_label="FACT",
            verdict="FAIL",
            confidence=1.5,
        )


def test_record_observer_gate_verdict_writes_run_and_finding() -> None:
    client = _FakeClient()
    repo = ResearchRepo(client)

    result = repo.record_observer_gate_verdict(
        run_key="observer_run",
        gate_result={
            "verdict": "FAIL",
            "status": "ACTIVE / GATE FAILED",
            "row_count": 10,
            "coverage_pct": 80.0,
            "p50_total_latency_ms": 595.0,
            "p90_total_latency_ms": 1200.0,
            "reasons": ["coverage below target"],
            "live_network_confirmed": False,
        },
    )

    assert result["truth_label"] == "RISK"
    assert client.calls[0]["table"] == "research_runs"
    assert client.calls[0]["on_conflict"] == "run_key"
    assert client.calls[1]["table"] == "research_findings"
    assert client.calls[1]["on_conflict"] == "run_key,finding_key"
    assert client.calls[1]["payload"]["finding_key"] == "observer_gate_verdict"

from __future__ import annotations

import csv
import sys
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

emitter = import_module("fast10_detector_emitter")
gate = import_module("observer_gate_eval")


def test_smoke_emitter_writes_observer_latency_live_csv(tmp_path: Path) -> None:
    output = tmp_path / "observer_latency_live.csv"

    emitter.write_smoke_latency_csv(
        output,
        rows=1,
        base_ts_ms=1_800_000_000_000,
        detector_latency_ms=95.0,
        quote_latency_ms=250.0,
    )

    with output.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert reader.fieldnames == gate.REQUIRED_FIELDS
    assert len(rows) == 1
    assert rows[0]["quote_ok"] == "true"
    assert rows[0]["detector_latency_ms"] == "95.0"
    assert rows[0]["quote_latency_ms"] == "250.0"
    assert rows[0]["total_latency_ms"] == "345.0"

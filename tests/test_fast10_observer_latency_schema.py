from __future__ import annotations

import csv
import sys
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

observer = import_module("fast10_observer")
gate = import_module("observer_gate_eval")


def test_fast10_observer_writes_mandatory_latency_schema(tmp_path: Path) -> None:
    output = tmp_path / "observer_latency_live.csv"
    row = {
        "signal_ts_ms": "1800000000000",
        "detected_ts_ms": "1800000000080",
        "quote_start_ts_ms": "1800000000080",
        "quote_end_ts_ms": "1800000000260",
        "detector_latency_ms": "80.0",
        "quote_latency_ms": "180.0",
        "total_latency_ms": "260.0",
        "quote_ok": "true",
        "error": "",
        "ignored_context": "not written",
    }

    observer.write_csv(output, [row])

    with output.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert reader.fieldnames == gate.REQUIRED_FIELDS
    assert rows == [{field: row[field] for field in gate.REQUIRED_FIELDS}]

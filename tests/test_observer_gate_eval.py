from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

gate = import_module("observer_gate_eval")


def make_latency_row(
    index: int,
    *,
    detector_latency_ms: float = 80.0,
    quote_latency_ms: float = 180.0,
    quote_ok: str = "true",
) -> dict[str, str]:
    signal_ts_ms = 1_800_000_000_000 + index * 1_000
    detected_ts_ms = signal_ts_ms + detector_latency_ms
    quote_start_ts_ms = detected_ts_ms
    quote_end_ts_ms = quote_start_ts_ms + quote_latency_ms
    return {
        "signal_ts_ms": str(signal_ts_ms),
        "detected_ts_ms": str(detected_ts_ms),
        "quote_start_ts_ms": str(quote_start_ts_ms),
        "quote_end_ts_ms": str(quote_end_ts_ms),
        "detector_latency_ms": str(detector_latency_ms),
        "quote_latency_ms": str(quote_latency_ms),
        "total_latency_ms": str(detector_latency_ms + quote_latency_ms),
        "quote_ok": quote_ok,
        "error": "" if quote_ok == "true" else "timeout",
    }


def test_live_gate_passes_when_coverage_and_total_latency_meet_targets() -> None:
    rows = [make_latency_row(index) for index in range(50)]

    result = gate.evaluate_rows(rows, run_mode="live", min_live_rows=50)

    assert result["verdict"] == "PASS"
    assert result["coverage_pct"] == 100.0
    assert result["p50_total_latency_ms"] == 260.0
    assert result["p90_quote_latency_ms"] == 180.0
    assert result["p90_detector_latency_ms"] == 80.0


def test_missing_required_latency_field_fails_gate() -> None:
    row = make_latency_row(1)
    del row["quote_start_ts_ms"]

    result = gate.evaluate_rows([row], run_mode="live", min_live_rows=1)

    assert result["verdict"] == "FAIL"
    assert "quote_start_ts_ms" in result["missing_fields"]


def test_quote_failures_count_against_coverage() -> None:
    rows = [make_latency_row(index) for index in range(8)]
    rows.extend(make_latency_row(index, quote_ok="false") for index in range(8, 10))

    result = gate.evaluate_rows(rows, run_mode="live", min_live_rows=10)

    assert result["verdict"] == "FAIL"
    assert result["coverage_pct"] == 80.0
    assert result["quote_success_count"] == 8


def test_smoke_run_is_marked_smoke_only_and_not_live_worded() -> None:
    result = gate.evaluate_rows([make_latency_row(1)], run_mode="smoke", min_live_rows=50)
    report = gate.render_report(result, source_label="observer_latency_live.csv")

    assert result["verdict"] == "SMOKE_ONLY"
    assert "Observer harness validated; live network run pending" in report
    assert "capturing live signals" not in report.lower()
    assert "measuring reality" not in report.lower()

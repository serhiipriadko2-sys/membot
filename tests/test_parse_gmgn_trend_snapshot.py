from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "10_parse_gmgn_trend_snapshot.py"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "gmgn_trend_snapshot_sample.json"

spec = importlib.util.spec_from_file_location("gmgn_trend_parser", SCRIPT)
parser = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(parser)


def read_rows(path: Path):
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_parse_snapshot_rows_preserve_raw_metrics(tmp_path):
    output = tmp_path / "gmgn_trend_snapshots.csv"
    out, count = parser.run(FIXTURE, output, snapshot_ts="2026-05-17T00:00:00+00:00")

    assert out == output
    assert count == 2
    rows = read_rows(output)
    assert rows[0]["token_name"] == "SCHIZO"
    assert rows[0]["token_mint"] == "62t1E5e2h6XCJk78D3x1NMUzX6TQGhmnj7AxeQSypump"
    assert rows[0]["age_seconds"] == "60"
    assert rows[0]["raw_metric_a"] == "7%"
    assert rows[0]["raw_metric_g"] == "2 / 7.1%"
    assert rows[0]["token_info_raw"] == "DS"
    assert rows[1]["has_telegram"] == "true"


def test_parser_does_not_emit_buy_signals_or_source_action(tmp_path):
    output = tmp_path / "gmgn_trend_snapshots.csv"
    parser.run(FIXTURE, output, snapshot_ts="2026-05-17T00:00:00+00:00")
    rows = read_rows(output)

    forbidden_columns = {"action", "buy_signal", "sell_signal", "recommendation", "signal"}
    assert forbidden_columns.isdisjoint(rows[0].keys())
    assert "source_action_ignored_not_signal" in rows[0]["parse_notes"]


def test_non_json_snapshot_is_stored_but_not_parsed(tmp_path):
    raw = tmp_path / "trend.html"
    raw.write_text("<html><body>GMGN Trend dynamic snapshot</body></html>", encoding="utf-8")
    output = tmp_path / "gmgn_trend_snapshots.csv"
    _, count = parser.run(raw, output, snapshot_ts="2026-05-17T00:00:00+00:00")

    assert count == 0
    assert output.exists()
    rows = read_rows(output)
    assert rows == []

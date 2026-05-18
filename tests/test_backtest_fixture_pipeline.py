from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
FIXTURE = ROOT / "tests" / "fixtures" / "trade_export_sample.csv"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module

importer = load_module("trade_importer", ROOT / "scripts" / "11_import_trade_export.py")
fee_adjusted = load_module("fee_adjusted", ROOT / "scripts" / "12_fee_adjusted_pnl.py")
copy_stress = load_module("copy_stress", ROOT / "scripts" / "13_copy_stress_model.py")
reporter = load_module("backtest_report", ROOT / "scripts" / "14_backtest_report.py")


def write_rows(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_fixture_backtest_pipeline_creates_required_outputs(tmp_path):
    processed = tmp_path / "data" / "processed"
    reports = tmp_path / "reports"
    processed.mkdir(parents=True)
    reports.mkdir(parents=True)

    swaps = importer.import_rows(FIXTURE)
    wallet_swaps = processed / "wallet_swaps.csv"
    write_rows(wallet_swaps, swaps, importer.FIELDS)

    paired_rows = [
        {
            "token_mint": "A_MINT",
            "entry_signature": "buy_a_1",
            "exit_signature": "sell_a_1",
            "entry_time": "1710000000",
            "exit_time": "1710000060",
            "entry_usd": "100",
            "exit_usd": "125",
            "observed_fee_usd": "3",
            "hold_seconds": "60",
            "pairing_method": "fixture_fifo",
            "pairing_confidence": "high",
        },
        {
            "token_mint": "B_MINT",
            "entry_signature": "buy_b_1",
            "exit_signature": "sell_b_1",
            "entry_time": "1710000100",
            "exit_time": "1710000200",
            "entry_usd": "200",
            "exit_usd": "180",
            "observed_fee_usd": "",
            "hold_seconds": "100",
            "pairing_method": "fixture_fifo",
            "pairing_confidence": "medium",
        },
    ]
    trades_paired = processed / "trades_paired.csv"
    write_rows(trades_paired, paired_rows, list(paired_rows[0].keys()))

    fee_rows = fee_adjusted.calculate(paired_rows)
    fee_adjusted_path = processed / "fee_adjusted_pnl.csv"
    write_rows(fee_adjusted_path, fee_rows, fee_adjusted.FIELDS)

    stress_rows = copy_stress.stress_rows(fee_rows)
    stress_path = processed / "copy_stress_model.csv"
    write_rows(stress_path, stress_rows, copy_stress.FIELDS)

    report_text = reporter.generate_report(processed, real_dataset=False)
    report_path = reports / "backtest_report.md"
    report_path.write_text(report_text, encoding="utf-8")

    assert wallet_swaps.exists()
    assert fee_adjusted_path.exists()
    assert stress_path.exists()
    assert report_path.exists()
    assert len(read_rows(fee_adjusted_path)) == 2
    assert len(read_rows(stress_path)) == 12
    assert "real dataset: NOT RUN" in report_text
    assert "Copy-stress model is not latency replay." in report_text
    assert "latency_replay_status: UNKNOWN" in report_text

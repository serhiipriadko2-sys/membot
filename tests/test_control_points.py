from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

entry_context = import_module("18_build_entry_context")
control_points = import_module("19_build_control_points")


def test_entry_context_has_feature_metadata_columns() -> None:
    trades = [
        {"token_mint": "M1", "entry_signature": "e1", "exit_signature": "x1", "entry_time": "100", "exit_time": "160", "entry_slot": "10", "exit_slot": "20", "hold_seconds": "60", "entry_sol": "1", "exit_sol": "2", "token_amount": "100", "pnl_sol": "1", "net_pnl_sol": "1"},
        {"token_mint": "M1", "entry_signature": "e2", "exit_signature": "x2", "entry_time": "200", "exit_time": "260", "entry_slot": "30", "exit_slot": "40", "hold_seconds": "60", "entry_sol": "1", "exit_sol": "0.5", "token_amount": "100", "pnl_sol": "-0.5", "net_pnl_sol": "-0.5"},
    ]
    swaps = [
        {"signature": "p1", "token_mint": "M1", "side": "BUY", "block_time": "80", "slot": "5", "sol_amount": "0.7", "parse_confidence": "high"},
        {"signature": "e1", "token_mint": "M1", "side": "BUY", "block_time": "100", "slot": "10", "sol_amount": "1.0", "parse_confidence": "high"},
        {"signature": "e2", "token_mint": "M1", "side": "BUY", "block_time": "200", "slot": "30", "sol_amount": "1.0", "parse_confidence": "high"},
    ]
    price_series = [
        {"token_mint": "M1", "timestamp": "70", "slot": "3", "price_sol": "0.01", "signature": "price0"},
        {"token_mint": "M1", "timestamp": "80", "slot": "5", "price_sol": "0.02", "signature": "p1"},
    ]

    rows = entry_context.build_entry_context(swaps, trades, price_series, sample_winners=1, sample_losers=1, windows=[30])

    first = next(row for row in rows if row["entry_signature"] == "e1")
    families = set(first["feature_family"].split(";"))
    assert {"wallet_flow", "price_action"}.issubset(families)
    assert first["feature_source"] == "wallet_swaps;price_series"
    assert first["confidence"] == "medium"
    assert float(first["feature_coverage_pct"]) > 0


def test_control_points_are_pre_entry_and_wallet_derived() -> None:
    entries = [
        {"sample_id": "1", "entry_signature": "e1", "token_mint": "M1", "entry_time": "100", "entry_slot": "10"},
    ]
    swaps = [
        {"signature": "p1", "token_mint": "M1", "side": "BUY", "block_time": "20", "slot": "2", "sol_amount": "0.5", "parse_confidence": "high"},
        {"signature": "p2", "token_mint": "M1", "side": "SELL", "block_time": "35", "slot": "3", "sol_amount": "0.2", "parse_confidence": "high"},
        {"signature": "future", "token_mint": "M1", "side": "BUY", "block_time": "120", "slot": "12", "sol_amount": "9.0", "parse_confidence": "high"},
    ]
    price_series = [
        {"token_mint": "M1", "timestamp": "20", "slot": "2", "price_sol": "0.01", "signature": "p1"},
        {"token_mint": "M1", "timestamp": "35", "slot": "3", "price_sol": "0.02", "signature": "p2"},
        {"token_mint": "M1", "timestamp": "120", "slot": "12", "price_sol": "0.99", "signature": "future"},
    ]

    rows = control_points.build_control_points(entries, swaps, price_series, windows=[30], offsets=[-60])

    assert len(rows) == 1
    row = rows[0]
    assert row["control_type"] == "same_token_pre_entry"
    assert row["control_time"] == 40
    assert row["leakage_guard_ok"] == "true"
    assert row["market_coverage"] == "wallet_only"
    assert row["wallet_buy_count_30s"] == 1
    assert row["wallet_sell_count_30s"] == 1
    assert row["price_points_30s"] == 2
    assert row["market_volume_sol_30s"] == "UNKNOWN"


def test_after_controls_require_explicit_flag() -> None:
    entries = [{"sample_id": "1", "entry_signature": "e1", "token_mint": "M1", "entry_time": "100", "entry_slot": "10"}]

    no_after = control_points.build_control_points(entries, [], [], windows=[30], offsets=[30], include_after=False)
    with_after = control_points.build_control_points(entries, [], [], windows=[30], offsets=[30], include_after=True)

    assert no_after == []
    assert len(with_after) == 1
    assert with_after[0]["control_type"] == "same_token_post_entry"
    assert with_after[0]["leakage_guard_ok"] == "false"

from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

entry_context = import_module("18_build_entry_context")


def test_balanced_selection_and_leakage_guard_exclude_entry_and_future_rows() -> None:
    trades = [
        {"token_mint": "M1", "entry_signature": "e1", "exit_signature": "x1", "entry_time": "100", "exit_time": "160", "entry_slot": "10", "exit_slot": "20", "hold_seconds": "60", "entry_sol": "1", "exit_sol": "2", "token_amount": "100", "pnl_sol": "1", "net_pnl_sol": "1"},
        {"token_mint": "M1", "entry_signature": "e2", "exit_signature": "x2", "entry_time": "200", "exit_time": "260", "entry_slot": "30", "exit_slot": "40", "hold_seconds": "60", "entry_sol": "1", "exit_sol": "0.5", "token_amount": "100", "pnl_sol": "-0.5", "net_pnl_sol": "-0.5"},
        {"token_mint": "M2", "entry_signature": "e3", "exit_signature": "x3", "entry_time": "300", "exit_time": "360", "entry_slot": "50", "exit_slot": "60", "hold_seconds": "60", "entry_sol": "1", "exit_sol": "1.5", "token_amount": "100", "pnl_sol": "0.5", "net_pnl_sol": "0.5"},
        {"token_mint": "M2", "entry_signature": "e4", "exit_signature": "x4", "entry_time": "400", "exit_time": "460", "entry_slot": "70", "exit_slot": "80", "hold_seconds": "60", "entry_sol": "1", "exit_sol": "0.8", "token_amount": "100", "pnl_sol": "-0.2", "net_pnl_sol": "-0.2"},
    ]
    swaps = [
        {"signature": "p1", "token_mint": "M1", "side": "BUY", "block_time": "80", "slot": "5", "sol_amount": "0.7", "parse_confidence": "high"},
        {"signature": "e1", "token_mint": "M1", "side": "BUY", "block_time": "100", "slot": "10", "sol_amount": "1.0", "parse_confidence": "high"},
        {"signature": "future1", "token_mint": "M1", "side": "BUY", "block_time": "120", "slot": "12", "sol_amount": "9.0", "parse_confidence": "high"},
        {"signature": "e2", "token_mint": "M1", "side": "BUY", "block_time": "200", "slot": "30", "sol_amount": "1.0", "parse_confidence": "high"},
        {"signature": "e3", "token_mint": "M2", "side": "BUY", "block_time": "300", "slot": "50", "sol_amount": "1.0", "parse_confidence": "high"},
        {"signature": "e4", "token_mint": "M2", "side": "BUY", "block_time": "400", "slot": "70", "sol_amount": "1.0", "parse_confidence": "high"},
    ]
    price_series = [
        {"token_mint": "M1", "timestamp": "70", "slot": "3", "price_sol": "0.01", "signature": "price0"},
        {"token_mint": "M1", "timestamp": "80", "slot": "5", "price_sol": "0.02", "signature": "p1"},
        {"token_mint": "M1", "timestamp": "100", "slot": "10", "price_sol": "0.03", "signature": "e1"},
    ]

    rows = entry_context.build_entry_context(swaps, trades, price_series, sample_winners=2, sample_losers=2, windows=[30])

    assert len(rows) == 4
    assert sum(row["sample_class"] == "winner" for row in rows) == 2
    assert sum(row["sample_class"] == "loser" for row in rows) == 2
    first = next(row for row in rows if row["entry_signature"] == "e1")
    assert first["wallet_buy_count_30s"] == 1
    assert first["wallet_largest_buy_sol_30s"] == 0.7
    assert first["price_points_30s"] == 2
    assert first["price_return_30s"] == 1.0
    assert first["leakage_guard_ok"] == "true"


def test_missing_market_context_is_unknown_not_fabricated() -> None:
    trades = [
        {"token_mint": "M1", "entry_signature": "e1", "exit_signature": "x1", "entry_time": "100", "exit_time": "160", "entry_slot": "10", "exit_slot": "20", "hold_seconds": "60", "entry_sol": "1", "exit_sol": "2", "token_amount": "100", "pnl_sol": "1", "net_pnl_sol": "1"},
        {"token_mint": "M1", "entry_signature": "e2", "exit_signature": "x2", "entry_time": "200", "exit_time": "260", "entry_slot": "30", "exit_slot": "40", "hold_seconds": "60", "entry_sol": "1", "exit_sol": "0.5", "token_amount": "100", "pnl_sol": "-0.5", "net_pnl_sol": "-0.5"},
    ]
    swaps = [
        {"signature": "e1", "token_mint": "M1", "side": "BUY", "block_time": "100", "slot": "10", "sol_amount": "1.0", "parse_confidence": "high"},
        {"signature": "e2", "token_mint": "M1", "side": "BUY", "block_time": "200", "slot": "30", "sol_amount": "1.0", "parse_confidence": "high"},
    ]

    rows = entry_context.build_entry_context(swaps, trades, [], sample_winners=1, sample_losers=1, windows=[60])

    assert rows[0]["market_coverage"] == "wallet_only"
    assert rows[0]["market_volume_sol_60s"] == "UNKNOWN"
    assert rows[0]["token_age_seconds"] == "UNKNOWN"
    assert rows[0]["context_status"] == "UNKNOWN"

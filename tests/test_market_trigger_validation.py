from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

market_tests = import_module("29_test_market_triggers")


def test_split_market_context_separates_entry_and_controls() -> None:
    rows = [
        {"anchor_type": "entry", "market_tx_count_30s": "2"},
        {"anchor_type": "same_token_market_pre_entry", "market_tx_count_30s": "1"},
    ]

    entries, controls = market_tests.split_market_context(rows)

    assert len(entries) == 1
    assert len(controls) == 1


def test_market_trigger_tests_emit_expected_features() -> None:
    rows = [
        {"anchor_type": "entry", "market_tx_count_30s": "5", "market_volume_usd_30s": "100", "market_buy_count_30s": "4", "market_sell_count_30s": "1", "market_buy_sell_imbalance_30s": "0.6", "market_unique_buyers_30s": "4", "market_unique_sellers_30s": "1", "market_price_change_30s": "0.1", "market_tx_rate_30s": "0.166"},
        {"anchor_type": "entry", "market_tx_count_30s": "6", "market_volume_usd_30s": "120", "market_buy_count_30s": "5", "market_sell_count_30s": "1", "market_buy_sell_imbalance_30s": "0.66", "market_unique_buyers_30s": "5", "market_unique_sellers_30s": "1", "market_price_change_30s": "0.2", "market_tx_rate_30s": "0.2"},
        {"anchor_type": "control", "market_tx_count_30s": "1", "market_volume_usd_30s": "20", "market_buy_count_30s": "1", "market_sell_count_30s": "3", "market_buy_sell_imbalance_30s": "-0.5", "market_unique_buyers_30s": "1", "market_unique_sellers_30s": "3", "market_price_change_30s": "-0.1", "market_tx_rate_30s": "0.033"},
        {"anchor_type": "control", "market_tx_count_30s": "2", "market_volume_usd_30s": "30", "market_buy_count_30s": "1", "market_sell_count_30s": "4", "market_buy_sell_imbalance_30s": "-0.6", "market_unique_buyers_30s": "1", "market_unique_sellers_30s": "4", "market_price_change_30s": "-0.2", "market_tx_rate_30s": "0.066"},
    ]

    tests = market_tests.build_market_trigger_tests(rows, bootstrap_iters=20, top_k=2)

    assert tests
    assert {row["test_scope"] for row in tests} == {"entry_vs_control"}
    assert any(row["feature_id"] == "market_tx_count_30s" for row in tests)


def test_market_report_contains_guardrail() -> None:
    report = market_tests.render_market_report([], 2, 2)
    assert "Market-wide guardrail" in report
    assert "not a trading signal" in report

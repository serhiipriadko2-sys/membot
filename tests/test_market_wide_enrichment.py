from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

market_context = import_module("25_build_market_context")
market_controls = import_module("26_build_market_controls")
market_join = import_module("27_enrich_entry_context_market")
helius = import_module("28_build_helius_enrichment")


def test_market_context_computes_pre_entry_stats_only() -> None:
    entries = [{"entry_signature": "entry", "token_mint": "M1", "entry_time": "1000", "entry_slot": "100"}]
    trades = [
        {"tx_id": "a", "block_time": "970", "block_slot": "90", "token_bought_mint_address": "M1", "amount_usd": "100", "token_bought_price": "1", "buyer": "b1"},
        {"tx_id": "b", "block_time": "980", "block_slot": "91", "token_sold_mint_address": "M1", "amount_usd": "50", "token_sold_price": "1.1", "seller": "s1"},
        {"tx_id": "future", "block_time": "1010", "block_slot": "110", "token_bought_mint_address": "M1", "amount_usd": "999", "token_bought_price": "9", "buyer": "b2"},
    ]

    rows = market_context.build_market_context(market_context.anchors_from_entries(entries), trades, [30])

    assert len(rows) == 1
    row = rows[0]
    assert row["context_status"] == "PARTIAL"
    assert row["market_tx_count_30s"] == 2
    assert row["market_buy_count_30s"] == 1
    assert row["market_sell_count_30s"] == 1
    assert row["market_unique_buyers_30s"] == 1
    assert row["market_unique_sellers_30s"] == 1
    assert float(row["market_price_change_30s"]) > 0


def test_market_controls_select_same_token_before_entry() -> None:
    entries = [{"entry_signature": "entry", "token_mint": "M1", "entry_time": "1000", "entry_slot": "100"}]
    trades = [
        {"tx_id": "a", "block_time": "700", "block_slot": "70", "token_bought_mint_address": "M1", "amount_usd": "100"},
        {"tx_id": "b", "block_time": "950", "block_slot": "95", "token_bought_mint_address": "M1", "amount_usd": "100"},
        {"tx_id": "entry", "block_time": "1000", "block_slot": "100", "token_bought_mint_address": "M1", "amount_usd": "100"},
        {"tx_id": "other", "block_time": "960", "block_slot": "96", "token_bought_mint_address": "M2", "amount_usd": "100"},
    ]

    rows = market_controls.build_market_controls(entries, trades, controls_per_entry=2, min_offset_seconds=30, max_offset_seconds=400)

    assert len(rows) == 2
    assert rows[0]["control_signature"] == "b"
    assert rows[0]["leakage_guard_ok"] == "true"
    assert all(row["token_mint"] == "M1" for row in rows)


def test_market_join_preserves_unknown_when_missing_market_row() -> None:
    entries = [{"entry_signature": "e1", "token_mint": "M1", "entry_time": "100", "foo": "bar"}]

    rows, fields = market_join.enrich_entry_context(entries, [])

    assert rows[0]["market_enriched"] == "false"
    assert rows[0]["market_context_status"] == "UNKNOWN"
    assert "market_enriched" in fields


def test_helius_parser_counts_transfers_and_balance_changes() -> None:
    payload = [
        {
            "signature": "sig",
            "timestamp": 123,
            "slot": 456,
            "fee": 5000,
            "nativeTransfers": [{"fromUserAccount": "a"}],
            "tokenTransfers": [{"mint": "M1"}, {"mint": "M2"}],
            "accountData": [{"tokenBalanceChanges": [{"mint": "M1"}]}],
        }
    ]

    rows = helius.build_helius_enrichment(payload)

    assert rows[0]["signature"] == "sig"
    assert rows[0]["native_transfer_count"] == 1
    assert rows[0]["token_transfer_count"] == 2
    assert rows[0]["token_balance_change_count"] == 1

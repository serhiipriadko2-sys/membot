from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

cluster_validation = import_module("23_test_cluster_triggers")
cross_validation = import_module("24_test_cross_chain_triggers")


def test_controls_to_anchor_entries_uses_control_time() -> None:
    controls = [
        {"control_id": "7", "entry_signature": "entry", "token_mint": "M1", "control_time": "940", "control_slot": "90"},
        {"control_id": "8", "entry_signature": "entry2", "token_mint": "M2", "control_time": "", "control_slot": ""},
    ]

    anchors = cluster_validation.controls_to_anchor_entries(controls)

    assert anchors == [
        {
            "entry_signature": "control:7:entry",
            "token_mint": "M1",
            "entry_time": "940",
            "entry_slot": "90",
            "sample_class": "control",
        }
    ]


def test_cluster_trigger_tests_produce_entry_vs_control_rows() -> None:
    entries = [{"entry_signature": "entry", "token_mint": "M1", "entry_time": "1000", "entry_slot": "100"}]
    controls = [{"control_id": "1", "entry_signature": "entry", "token_mint": "M1", "control_time": "900", "control_slot": "80"}]
    swaps = [
        {"signature": "a", "wallet": "w1", "token_mint": "M1", "side": "BUY", "block_time": "970", "slot": "90", "amount_usd": "100", "token_amount": "1000", "price_usd": "0.1", "funding_source": "f1", "route": "pump"},
        {"signature": "b", "wallet": "w2", "token_mint": "M1", "side": "BUY", "block_time": "975", "slot": "91", "amount_usd": "101", "token_amount": "1000", "price_usd": "0.1", "funding_source": "f1", "route": "pump"},
        {"signature": "c", "wallet": "w3", "token_mint": "M1", "side": "BUY", "block_time": "980", "slot": "92", "amount_usd": "102", "token_amount": "1000", "price_usd": "0.1", "funding_source": "f1", "route": "pump"},
    ]

    rows = cluster_validation.build_cluster_trigger_tests(entries, controls, swaps, window=300, min_wallets=3, bootstrap_iters=20, top_k=2)

    assert rows
    assert {row["test_scope"] for row in rows} == {"entry_vs_control"}
    assert any(row["feature_id"] == "cluster_presence_score" for row in rows)


def test_cross_chain_trigger_tests_produce_regime_rows() -> None:
    entries = [{"entry_signature": "entry", "token_mint": "M1", "entry_time": "7200", "entry_slot": "100"}]
    controls = [{"control_id": "1", "entry_signature": "entry", "token_mint": "M1", "control_time": "3600", "control_slot": "80"}]
    events = [
        {"event_id": "e1", "chain": "ethereum", "event_type": "bridge_flow", "timestamp": "7000", "block_number": "1", "token_address": "eth", "amount_usd": "10000", "amount_native": "5", "actor_address": "a"},
        {"event_id": "e2", "chain": "bsc", "event_type": "dex_volume_spike", "timestamp": "7100", "block_number": "2", "token_address": "bsc", "amount_usd": "20000", "amount_native": "10", "actor_address": "b"},
    ]

    rows = cross_validation.build_cross_chain_trigger_tests(entries, controls, events, window=900, bootstrap_iters=20, top_k=2)

    assert rows
    assert {row["test_scope"] for row in rows} == {"entry_vs_control"}
    assert any(row["feature_id"] == "combined_momentum" for row in rows)


def test_cross_chain_render_report_has_guardrail() -> None:
    report = cross_validation.render_cross_chain_report([], 1, 3)
    assert "Cross-chain guardrail" in report

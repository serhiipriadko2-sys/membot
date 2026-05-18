from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

cluster_builder = import_module("21_build_cluster_context")
cross_builder = import_module("22_build_cross_chain_context")
orch = import_module("trigger_orchestration_system")
triggers = import_module("20_test_entry_triggers")


def test_cluster_context_detects_multi_wallet_pre_entry_cluster() -> None:
    entries = [{"entry_signature": "entry", "token_mint": "M1", "entry_time": "1000", "entry_slot": "100"}]
    swaps = [
        {"signature": "a", "wallet": "w1", "token_mint": "M1", "side": "BUY", "block_time": "970", "slot": "90", "amount_usd": "100", "token_amount": "1000", "price_usd": "0.1", "funding_source": "f1", "route": "pump"},
        {"signature": "b", "wallet": "w2", "token_mint": "M1", "side": "BUY", "block_time": "975", "slot": "91", "amount_usd": "105", "token_amount": "1000", "price_usd": "0.1", "funding_source": "f1", "route": "pump"},
        {"signature": "c", "wallet": "w3", "token_mint": "M1", "side": "BUY", "block_time": "980", "slot": "92", "amount_usd": "98", "token_amount": "1000", "price_usd": "0.1", "funding_source": "f1", "route": "pump"},
        {"signature": "entry", "wallet": "target", "token_mint": "M1", "side": "BUY", "block_time": "1000", "slot": "100", "amount_usd": "100", "token_amount": "1000", "price_usd": "0.1"},
    ]

    rows = cluster_builder.build_cluster_context(entries, swaps, window=60, min_wallets=3)

    assert len(rows) == 1
    row = rows[0]
    assert row["context_status"] == "PARTIAL"
    assert int(row["cluster_wallet_count_30s"]) == 3
    assert float(row["cluster_presence_score"]) > 0
    assert float(row["cluster_toxicity_score"]) > 0


def test_cluster_context_unknown_when_only_target_wallet_seen() -> None:
    entries = [{"entry_signature": "entry", "token_mint": "M1", "entry_time": "1000", "entry_slot": "100"}]
    swaps = [{"signature": "a", "token_mint": "M1", "side": "BUY", "block_time": "970", "slot": "90", "amount_usd": "100"}]

    rows = cluster_builder.build_cluster_context(entries, swaps, window=60, min_wallets=2)

    assert rows[0]["context_status"] == "UNKNOWN"
    assert "insufficient distinct wallets" in rows[0]["notes"]


def test_cross_chain_context_marks_missing_events_unknown() -> None:
    entries = [{"entry_signature": "entry", "token_mint": "M1", "entry_time": "1000", "entry_slot": "100"}]

    rows = cross_builder.build_cross_chain_context(entries, [], window=900)

    assert rows[0]["context_status"] == "UNKNOWN"
    assert rows[0]["recommendation"] == "UNKNOWN"


def test_cross_chain_context_builds_regime_row_from_events() -> None:
    entries = [{"entry_signature": "entry", "token_mint": "M1", "entry_time": "7200", "entry_slot": "100"}]
    events = [
        {"event_id": "e1", "chain": "ethereum", "event_type": "bridge_flow", "timestamp": "7000", "block_number": "1", "token_address": "eth", "amount_usd": "10000", "amount_native": "5", "actor_address": "a"},
        {"event_id": "e2", "chain": "ethereum", "event_type": "dex_volume_spike", "timestamp": "7100", "block_number": "2", "token_address": "eth", "amount_usd": "20000", "amount_native": "10", "actor_address": "b"},
        {"event_id": "e3", "chain": "bsc", "event_type": "bridge_flow", "timestamp": "7100", "block_number": "3", "token_address": "bsc", "amount_usd": "15000", "amount_native": "10", "actor_address": "c"},
    ]

    rows = cross_builder.build_cross_chain_context(entries, events, window=900)

    assert rows[0]["context_status"] == "PARTIAL"
    assert rows[0]["target_chain"] == "solana"
    assert float(rows[0]["bridge_inflow_usd_15m"]) > 0


def test_orchestrator_cluster_filter_does_not_apply_unrelated_cluster() -> None:
    token = orch.TokenMetrics(
        mint="M1", name="T", symbol="T", price_usd=0.01,
        price_change_1m=1, price_change_5m=1, price_change_15m=1, price_change_1h=1,
        volume_24h=100000, volume_1h=10000, volume_30m=5000,
        liquidity_usd=20000, market_cap_usd=200000, holder_count=100, top10_holder_pct=20,
        tx_count_1h=10, buy_count_1h=7, sell_count_1h=3, created_at=0, age_minutes=10,
        mint_authority_revoked=True, freeze_authority_revoked=True,
        metadata={"feature_coverage_pct": 80, "cluster_score": 0},
    )
    orchestrator = orch.TriggerOrchestrator({"thresholds": {"require_cluster_support": False}})
    orchestrator.update_cluster_data("c1", {"tokens": ["OTHER"], "cluster_quality_score": 90, "cluster_toxicity_score": 0})

    assert orchestrator.calculate_cluster_score(token) == 0


def test_orchestrator_optional_cross_chain_does_not_force_avoid() -> None:
    token = orch.TokenMetrics(
        mint="M1", name="T", symbol="T", price_usd=0.01,
        price_change_1m=20, price_change_5m=20, price_change_15m=10, price_change_1h=20,
        volume_24h=100000, volume_1h=20000, volume_30m=10000,
        liquidity_usd=20000, market_cap_usd=200000, holder_count=100, top10_holder_pct=20,
        tx_count_1h=100, buy_count_1h=80, sell_count_1h=20, created_at=0, age_minutes=10,
        mint_authority_revoked=True, freeze_authority_revoked=True,
        metadata={"feature_coverage_pct": 80, "cluster_score": 50},
    )
    orchestrator = orch.TriggerOrchestrator()
    orchestrator.update_token_data(token)

    signal = orchestrator.score_token("M1")

    assert "CROSS_CHAIN_UNVERIFIED" not in signal.reason_codes


def test_weighted_effect_size_handles_unequal_groups() -> None:
    xs = [10.0, 11.0]
    ys = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]

    assert triggers.pooled_effect_size(xs, ys) > 0

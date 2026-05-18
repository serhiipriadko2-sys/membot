from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

acd = import_module('advanced_coordinated_wallet_detector')
cc = import_module('cross_chain_sentiment_monitor')
to = import_module('trigger_orchestration_system')


def tx(wallet: str, token: str = 'M1', side: str = 'buy', amount: float = 100.0, ts: int = 1000, funding: str = ''):
    return acd.TransactionEvent(
        tx_hash=f'{wallet}-{token}-{side}-{ts}', wallet=wallet, token_mint=token, side=side,
        amount_usd=amount, amount_tokens=1000, price_usd=0.01, timestamp=ts, slot=ts,
        block=ts, dex='pump_fun', funding_source=funding,
    )


def test_empty_cluster_does_not_crash():
    detector = acd.CoordinatedWalletDetector()
    assert detector._classify_coordination_type([], []) == acd.CoordinationType.UNKNOWN


def test_new_wallets_without_history_do_not_create_precluster_signal():
    detector = acd.CoordinatedWalletDetector()
    assert detector.detect_pre_cluster_signals('M1', {'fresh1', 'fresh2'}) == []


def test_simultaneous_entry_detected_and_toxicity_is_signed():
    detector = acd.CoordinatedWalletDetector(cluster_size_min=2, cooccurrence_threshold=1)
    for i, wallet in enumerate(['w1', 'w2', 'w3']):
        detector.add_transaction(tx(wallet, amount=100.0, ts=1000 + i, funding='funder1'))
        detector.add_transaction(tx(wallet, side='sell', amount=95.0, ts=1030 + i, funding='funder1'))
    clusters = detector.detect_clusters()
    assert clusters
    cluster = next(iter(clusters.values()))
    assert cluster.coordination_type in {
        acd.CoordinationType.SIMULTANEOUS_ENTRY,
        acd.CoordinationType.SEQUENTIAL_ENTRY,
        acd.CoordinationType.PUMP_COORDINATION,
    }
    assert cluster.cluster_presence_score > 0
    assert cluster.cluster_toxicity_score > 0
    assert cluster.funding_source_similarity > 0


def test_cross_chain_event_dataclass_constructs():
    event = cc.CrossChainEvent(
        event_id='e1', chain=cc.Chain.ETHEREUM, event_type=cc.ActivityType.LARGE_TRANSFER,
        timestamp=100, block_number=1, token_address='0xtoken', amount_usd=1000,
        amount_native=1, actor_address='0xactor', token_symbol='TOK'
    )
    assert event.amount_usd == 1000
    assert event.token_symbol == 'TOK'


def test_generate_leading_recommendation_no_keyerror():
    monitor = cc.CrossChainMonitor(now=7200)
    flow = cc.SentimentFlow(
        source_chain=cc.Chain.ETHEREUM, target_chain=cc.Chain.SOLANA, flow_direction='inflow',
        volume_24h=1000, tx_count_24h=10, avg_transaction_size=100, velocity=0.7,
        momentum=70, predicted_movement='bullish', confidence=90, time_to_impact=900,
    )
    assert monitor._generate_leading_recommendation([{'flow': flow}]) == 'STRONG_BUY'


def test_arbitrage_opportunity_has_prices_map():
    monitor = cc.CrossChainMonitor(now=123)
    opp = monitor._create_arbitrage_opportunity('token', 'ethereum', 'solana', 1.0, 1.02, 2.0, {'ethereum': 1.0, 'solana': 1.02})
    assert opp.prices == {'ethereum': 1.0, 'solana': 1.02}


class FakeCrossChainMonitor:
    def score_token(self, token):
        return 75.0


def sample_token(**kwargs):
    values = dict(
        mint='M1', name='Token', symbol='TOK', price_usd=0.01,
        price_change_1m=5, price_change_5m=8, price_change_15m=10, price_change_1h=12,
        volume_24h=100000, volume_1h=20000, volume_30m=10000,
        liquidity_usd=20000, market_cap_usd=200000, holder_count=200, top10_holder_pct=35,
        tx_count_1h=100, buy_count_1h=70, sell_count_1h=30, created_at=0, age_minutes=30,
        mint_authority_revoked=True, freeze_authority_revoked=True,
        metadata={'feature_coverage_pct': 80, 'cluster_score': 50},
    )
    values.update(kwargs)
    return to.TokenMetrics(**values)


def test_safety_gate_forces_avoid_on_low_liquidity():
    orchestrator = to.TriggerOrchestrator({'cross_chain_monitor': FakeCrossChainMonitor()})
    token = sample_token(liquidity_usd=1000)
    orchestrator.update_token_data(token)
    signal = orchestrator.score_token('M1')
    assert signal.action == 'AVOID'
    assert 'LOW_LIQUIDITY' in signal.risk_factors


def test_cross_chain_monitor_interface_used():
    orchestrator = to.TriggerOrchestrator({'cross_chain_monitor': FakeCrossChainMonitor()})
    token = sample_token()
    assert orchestrator.calculate_cross_chain_score(token) == 75.0

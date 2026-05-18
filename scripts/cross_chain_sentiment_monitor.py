#!/usr/bin/env python3
"""Cross-chain sentiment monitor v0.1.

Cross-chain data is treated as a regime filter, not a direct token BUY trigger.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from statistics import mean
from typing import Any


class Chain(Enum):
    ETHEREUM = "ethereum"
    SOLANA = "solana"
    BSC = "bsc"
    BASE = "base"
    ARBITRUM = "arbitrum"


class ActivityType(Enum):
    LARGE_TRANSFER = "large_transfer"
    BRIDGE_FLOW = "bridge_flow"
    DEX_VOLUME_SPIKE = "dex_volume_spike"
    NEW_TOKEN_LAUNCH = "new_token_launch"


@dataclass
class CrossChainEvent:
    event_id: str
    chain: Chain
    event_type: ActivityType
    timestamp: int
    block_number: int
    token_address: str
    amount_usd: float
    amount_native: float
    actor_address: str
    token_symbol: str | None = None
    actor_label: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    related_chains: set[Chain] = field(default_factory=set)


@dataclass
class SentimentFlow:
    source_chain: Chain
    target_chain: Chain
    flow_direction: str
    volume_24h: float
    tx_count_24h: int
    avg_transaction_size: float
    velocity: float
    momentum: float
    predicted_movement: str
    confidence: float
    time_to_impact: int


@dataclass
class ArbitrageOpportunity:
    opportunity_id: str
    token: str
    token_symbol: str
    prices: dict[str, float]
    price_differences: dict[tuple[str, str], float]
    estimated_profit_pct: float
    estimated_profit_usd: float
    net_profit_after_fees: float
    required_capital: float
    bridge_time_seconds: int
    risk_level: str
    detected_at: int
    expiry_timestamp: int
    urgency: str


class CrossChainMonitor:
    def __init__(self, now: int | None = None) -> None:
        self.now = now or 0
        self.events_by_chain: dict[Chain, list[CrossChainEvent]] = defaultdict(list)
        self.sentiment_flows: dict[tuple[Chain, Chain], SentimentFlow] = {}
        self.active_arbitrage: list[ArbitrageOpportunity] = []

    def add_event(self, event: CrossChainEvent) -> None:
        self.events_by_chain[event.chain].append(event)
        self.now = max(self.now, event.timestamp)

    def add_event_batch(self, events: list[CrossChainEvent]) -> None:
        for event in events:
            self.add_event(event)

    def _recent_events(self, chain: Chain, seconds: int = 86400) -> list[CrossChainEvent]:
        cutoff = self.now - seconds
        return [event for event in self.events_by_chain.get(chain, []) if event.timestamp >= cutoff]

    def calculate_flow(self, source_chain: Chain, target_chain: Chain) -> SentimentFlow:
        current = [e for e in self._recent_events(source_chain, 3600) if e.amount_usd > 0]
        previous = [e for e in self.events_by_chain.get(source_chain, []) if self.now - 7200 <= e.timestamp < self.now - 3600]
        current_volume = sum(e.amount_usd for e in current)
        previous_volume = sum(e.amount_usd for e in previous)
        velocity = (current_volume / max(1.0, previous_volume)) - 1.0 if previous_volume else 0.0
        momentum = abs(velocity) * 100.0
        predicted = "bullish" if velocity > 0.3 else "bearish" if velocity < -0.3 else "neutral"
        return SentimentFlow(
            source_chain=source_chain,
            target_chain=target_chain,
            flow_direction="inflow" if current_volume > previous_volume else "balanced",
            volume_24h=sum(e.amount_usd for e in self._recent_events(source_chain, 86400)),
            tx_count_24h=len(self._recent_events(source_chain, 86400)),
            avg_transaction_size=current_volume / max(1, len(current)),
            velocity=velocity,
            momentum=momentum,
            predicted_movement=predicted,
            confidence=min(95.0, 50.0 + momentum),
            time_to_impact=900,
        )

    def detect_leading_signals(self, target_chain: Chain = Chain.SOLANA) -> dict[str, Any]:
        signals: list[dict[str, Any]] = []
        for chain in Chain:
            if chain == target_chain:
                continue
            flow = self.calculate_flow(chain, target_chain)
            if flow.momentum > 20:
                signals.append({"source_chain": chain.value, "flow": flow})
        return {
            "target_chain": target_chain.value,
            "leading_signals": signals,
            "combined_momentum": mean([s["flow"].momentum for s in signals]) if signals else 0.0,
            "signal_count": len(signals),
            "recommendation": self._generate_leading_recommendation(signals),
        }

    def _generate_leading_recommendation(self, signals: list[dict[str, Any]]) -> str:
        if not signals:
            return "NO_SIGNALS"
        avg_momentum = mean([s["flow"].momentum for s in signals])
        if avg_momentum > 60:
            return "STRONG_BUY"
        if avg_momentum > 40:
            return "BUY"
        if avg_momentum > 20:
            return "WATCH"
        return "NEUTRAL"

    def _create_arbitrage_opportunity(
        self,
        token: str,
        chain_a: str,
        chain_b: str,
        price_a: float,
        price_b: float,
        diff_pct: float,
        prices_map: dict[str, float],
    ) -> ArbitrageOpportunity:
        fees_pct = 0.6
        net_profit_pct = diff_pct - fees_pct
        required_capital = 10000.0
        profit_usd = required_capital * net_profit_pct / 100.0
        risk_level = "high" if diff_pct > 2 else "medium" if diff_pct > 1 else "low"
        return ArbitrageOpportunity(
            opportunity_id=f"arb_{token[:8]}_{chain_a}_{chain_b}_{self.now}",
            token=token,
            token_symbol="TOKEN",
            prices=dict(prices_map),
            price_differences={(chain_a, chain_b): diff_pct},
            estimated_profit_pct=net_profit_pct,
            estimated_profit_usd=profit_usd,
            net_profit_after_fees=profit_usd,
            required_capital=required_capital,
            bridge_time_seconds=300,
            risk_level=risk_level,
            detected_at=self.now,
            expiry_timestamp=self.now + (60 if risk_level == "high" else 180),
            urgency="critical" if risk_level == "high" else "normal",
        )

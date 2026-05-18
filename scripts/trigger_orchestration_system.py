#!/usr/bin/env python3
"""Reject-first trigger orchestration system v0.2.

Scoring is allowed only after SafetyGate. This module is a research contract,
not a production trading bot.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any


@dataclass
class TokenMetrics:
    mint: str
    name: str
    symbol: str
    price_usd: float
    price_change_1m: float
    price_change_5m: float
    price_change_15m: float
    price_change_1h: float
    volume_24h: float
    volume_1h: float
    volume_30m: float
    liquidity_usd: float
    market_cap_usd: float
    holder_count: int
    top10_holder_pct: float
    tx_count_1h: int
    buy_count_1h: int
    sell_count_1h: int
    created_at: int
    age_minutes: int
    mint_authority_revoked: bool
    freeze_authority_revoked: bool
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MarketContext:
    sol_price: float
    btc_price: float
    fear_greed_index: int
    market_direction: str
    eth_gas_gwei: float
    bnb_gas_gwei: float
    social_volume_24h: float
    search_trend_score: float
    sol_price_change_pct: float = 0.0


@dataclass
class TriggerSignal:
    token_mint: str
    action: str
    composite_score: float
    confidence: float
    position_size_pct: float
    risk_factors: list[str]
    reason_codes: list[str]
    component_scores: dict[str, float]
    supporting_evidence: list[dict[str, Any]] = field(default_factory=list)


class TriggerOrchestrator:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = self._default_config()
        if config:
            for key, value in config.items():
                if isinstance(value, dict) and isinstance(self.config.get(key), dict):
                    self.config[key].update(value)
                else:
                    self.config[key] = value
        self.weights = self.config["weights"]
        self.thresholds = self.config["thresholds"]
        self.token_cache: dict[str, TokenMetrics] = {}
        self.market_context: MarketContext | None = None
        self.cross_chain_monitor: Any | None = self.config.get("cross_chain_monitor")
        self.active_clusters: dict[str, Any] = {}
        self.signal_history: list[TriggerSignal] = []

    def _default_config(self) -> dict[str, Any]:
        return {
            "weights": {"pecs": 0.30, "tma": 0.20, "lsa": 0.20, "cluster": 0.15, "cross_chain": 0.15},
            "thresholds": {
                "min_composite_score": 65,
                "min_feature_coverage_pct": 70,
                "min_liquidity_usd": 5000,
                "max_top10_holder_pct": 60,
                "require_cluster_support": True,
                "require_cross_chain_verified": False,
            },
            "position_sizing": {"strong_buy": 3.0, "buy": 2.0, "watch": 1.0, "avoid": 0.0},
        }

    def update_token_data(self, token: TokenMetrics) -> None:
        self.token_cache[token.mint] = token

    def update_market_context(self, context: MarketContext) -> None:
        self.market_context = context

    def update_cluster_data(self, cluster_id: str, cluster_data: Any) -> None:
        self.active_clusters[cluster_id] = cluster_data

    def calculate_pecs_score(self, token: TokenMetrics) -> float:
        momentum = min(100.0, max(0.0, 50.0 + token.price_change_5m * 4.0))
        volume = min(100.0, token.volume_1h / max(1.0, token.volume_24h / 24.0) * 20.0)
        safety = 50.0 + (25.0 if token.mint_authority_revoked else 0.0) + (25.0 if token.freeze_authority_revoked else 0.0)
        return min(100.0, momentum * 0.4 + volume * 0.3 + safety * 0.3)

    def calculate_tma_score(self, token: TokenMetrics) -> float:
        accel = token.price_change_5m - token.price_change_15m / 3.0
        tx_pressure = token.buy_count_1h / max(1, token.buy_count_1h + token.sell_count_1h)
        return min(100.0, max(0.0, 50.0 + accel * 4.0 + (tx_pressure - 0.5) * 60.0))

    def calculate_lsa_score(self, token: TokenMetrics) -> float:
        liq_ratio = token.liquidity_usd / max(1.0, token.market_cap_usd)
        return min(100.0, liq_ratio * 500.0)

    def _cluster_dict(self, cluster: Any) -> dict[str, Any]:
        if isinstance(cluster, dict):
            return cluster
        if is_dataclass(cluster):
            return asdict(cluster)
        return {
            key: getattr(cluster, key)
            for key in dir(cluster)
            if not key.startswith("_") and not callable(getattr(cluster, key))
        }

    def _cluster_matches_token(self, cluster: Any, token_mint: str) -> bool:
        data = self._cluster_dict(cluster)
        tokens = data.get("tokens") or data.get("token_mints") or data.get("mints")
        if tokens is None:
            return False
        if isinstance(tokens, str):
            tokens = [tokens]
        return token_mint in set(tokens)

    def calculate_cluster_score(self, token: TokenMetrics) -> float:
        clusters = [
            self._cluster_dict(cluster)
            for cluster in self.active_clusters.values()
            if self._cluster_matches_token(cluster, token.mint)
        ]
        if not clusters:
            return float(token.metadata.get("cluster_score", 0.0))
        best = max(clusters, key=lambda c: float(c.get("cluster_quality_score", 0.0)) - float(c.get("cluster_toxicity_score", 0.0)))
        return max(0.0, min(100.0, float(best.get("cluster_quality_score", 0.0)) - float(best.get("cluster_toxicity_score", 0.0))))

    def calculate_cross_chain_score(self, token: TokenMetrics) -> float:
        if self.cross_chain_monitor is not None:
            if hasattr(self.cross_chain_monitor, "score_token"):
                return float(self.cross_chain_monitor.score_token(token))
            if hasattr(self.cross_chain_monitor, "get_token_signal"):
                signal = self.cross_chain_monitor.get_token_signal(token.mint)
                if isinstance(signal, dict) and "score" in signal:
                    return float(signal["score"])
        if not self.market_context:
            return 30.0
        return min(100.0, 30.0 + max(0.0, self.market_context.sol_price_change_pct) * 5.0 + self.market_context.fear_greed_index * 0.2)

    def _feature_coverage_pct(self, token: TokenMetrics) -> float:
        return float(token.metadata.get("feature_coverage_pct", 0.0))

    def _safety_gate(self, token: TokenMetrics, cluster_score: float, cross_chain_verified: bool) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        if token.liquidity_usd < self.thresholds["min_liquidity_usd"]:
            reasons.append("LOW_LIQUIDITY")
        if token.top10_holder_pct > self.thresholds["max_top10_holder_pct"]:
            reasons.append("HIGH_CONCENTRATION")
        if not token.mint_authority_revoked or not token.freeze_authority_revoked:
            reasons.append("AUTHORITY_NOT_REVOKED")
        if self.thresholds.get("require_cluster_support", True) and cluster_score < 30:
            reasons.append("NO_CLUSTER_SUPPORT")
        if self.thresholds.get("require_cross_chain_verified", False) and not cross_chain_verified:
            reasons.append("CROSS_CHAIN_UNVERIFIED")
        if token.metadata.get("execution_decay_risk") == "HIGH":
            reasons.append("EXECUTION_DECAY_HIGH")
        if self._feature_coverage_pct(token) < self.thresholds["min_feature_coverage_pct"]:
            reasons.append("LOW_FEATURE_COVERAGE")
        return not reasons, reasons

    def score_token(self, mint: str) -> TriggerSignal | None:
        token = self.token_cache.get(mint)
        if token is None:
            return None
        scores = {
            "pecs": self.calculate_pecs_score(token),
            "tma": self.calculate_tma_score(token),
            "lsa": self.calculate_lsa_score(token),
            "cluster": self.calculate_cluster_score(token),
            "cross_chain": self.calculate_cross_chain_score(token),
        }
        safety_ok, reasons = self._safety_gate(token, scores["cluster"], self.cross_chain_monitor is not None)
        if not safety_ok:
            signal = TriggerSignal(mint, "AVOID", 0.0, 0.0, 0.0, reasons, reasons, scores, [{"type": "safety_gate", "positive": False}])
            self.signal_history.append(signal)
            return signal
        composite = sum(scores[key] * self.weights.get(key, 0.0) for key in scores)
        if composite >= 80:
            action, size = "STRONG_BUY", self.config["position_sizing"]["strong_buy"]
        elif composite >= 70:
            action, size = "BUY", self.config["position_sizing"]["buy"]
        elif composite >= self.thresholds["min_composite_score"]:
            action, size = "WATCH", self.config["position_sizing"]["watch"]
        else:
            action, size = "NO_ENTRY", 0.0
        signal = TriggerSignal(mint, action, composite, min(100.0, composite), size, [], [], scores)
        self.signal_history.append(signal)
        return signal

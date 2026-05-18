#!/usr/bin/env python3
"""Research-grade v0.1 coordinated-wallet detector.

The detector separates cluster presence from cluster quality and toxicity. A
coordinated cluster is not automatically bullish: sybil-like or dump-like
clusters receive toxicity instead of alpha.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from statistics import mean, pstdev
from typing import Any


class CoordinationType(Enum):
    UNKNOWN = "unknown"
    SIMULTANEOUS_ENTRY = "simultaneous_entry"
    SEQUENTIAL_ENTRY = "sequential_entry"
    PUMP_COORDINATION = "pump_coordination"
    DISTRIBUTED_COORDINATION = "distributed"
    ANTAGONISTIC = "antagonistic"


@dataclass
class TransactionEvent:
    tx_hash: str
    wallet: str
    token_mint: str
    side: str
    amount_usd: float
    amount_tokens: float
    price_usd: float
    timestamp: int
    slot: int
    block: int
    dex: str
    gas_fee_lamports: int = 0
    priority_fee_lamports: int = 0
    route: str = ""
    funding_source: str = ""


@dataclass
class WalletProfile:
    address: str
    first_seen: int
    total_volume_usd: float = 0.0
    total_trades: int = 0
    tokens_traded: set[str] = field(default_factory=set)
    win_rate: float = 0.0
    associated_addresses: set[str] = field(default_factory=set)


@dataclass
class ClusterMetrics:
    cluster_id: str
    wallet_count: int
    coordination_type: CoordinationType
    first_activity_timestamp: int
    last_activity_timestamp: int
    avg_entry_time_spread_seconds: float
    total_volume_usd: float
    combined_trade_count: int
    confidence_score: float
    cluster_presence_score: float
    cluster_quality_score: float
    cluster_toxicity_score: float
    cluster_lead_time_score: float
    cluster_exit_pressure_score: float
    funding_source_similarity: float
    position_size_similarity: float
    route_similarity: float


@dataclass
class PreClusterSignal:
    detected_at: int
    token_mint: str
    wallets_involved: list[str]
    trigger_type: str
    confidence_score: float
    notes: str = ""


class CoordinatedWalletDetector:
    def __init__(
        self,
        temporal_window_seconds: int = 300,
        cluster_size_min: int = 3,
        cooccurrence_threshold: int = 2,
    ) -> None:
        self.temporal_window = temporal_window_seconds
        self.cluster_size_min = cluster_size_min
        self.cooccurrence_threshold = cooccurrence_threshold
        self.transaction_history: dict[str, list[TransactionEvent]] = defaultdict(list)
        self.wallet_profiles: dict[str, WalletProfile] = {}
        self.token_wallets: dict[str, set[str]] = defaultdict(set)
        self.cluster_wallet_mapping: dict[str, set[str]] = {}
        self.active_clusters: dict[str, ClusterMetrics] = {}

    def add_transaction(self, tx: TransactionEvent) -> None:
        self.transaction_history[tx.wallet].append(tx)
        self.token_wallets[tx.token_mint].add(tx.wallet)
        profile = self.wallet_profiles.setdefault(tx.wallet, WalletProfile(address=tx.wallet, first_seen=tx.timestamp))
        profile.first_seen = min(profile.first_seen, tx.timestamp)
        profile.total_volume_usd += tx.amount_usd
        profile.total_trades += 1
        profile.tokens_traded.add(tx.token_mint)
        if tx.funding_source:
            profile.associated_addresses.add(tx.funding_source)

    def _token_overlap(self, a: str, b: str) -> int:
        ta = {tx.token_mint for tx in self.transaction_history.get(a, [])}
        tb = {tx.token_mint for tx in self.transaction_history.get(b, [])}
        return len(ta & tb)

    def detect_clusters(self) -> dict[str, ClusterMetrics]:
        clusters: dict[str, ClusterMetrics] = {}
        seen: set[frozenset[str]] = set()
        for _token, wallets in self.token_wallets.items():
            if len(wallets) < self.cluster_size_min:
                continue
            coordinated: set[str] = set()
            for wallet in wallets:
                if any(self._token_overlap(wallet, other) >= self.cooccurrence_threshold for other in wallets if other != wallet):
                    coordinated.add(wallet)
            if len(coordinated) < self.cluster_size_min:
                coordinated = set(wallets)
            key = frozenset(coordinated)
            if key in seen:
                continue
            seen.add(key)
            cluster_id = f"cluster_{len(clusters)}_{sorted(coordinated)[0][:8]}"
            metrics = self._calculate_cluster_metrics(cluster_id, sorted(coordinated))
            clusters[cluster_id] = metrics
            self.cluster_wallet_mapping[cluster_id] = coordinated
        self.active_clusters = clusters
        return clusters

    def _cluster_txs(self, wallets: list[str]) -> list[TransactionEvent]:
        return sorted([tx for wallet in wallets for tx in self.transaction_history.get(wallet, [])], key=lambda tx: (tx.timestamp, tx.slot, tx.tx_hash))

    def _calculate_cluster_metrics(self, cluster_id: str, wallets: list[str]) -> ClusterMetrics:
        txs = self._cluster_txs(wallets)
        coord_type = self._classify_coordination_type(wallets, txs)
        timestamps = [tx.timestamp for tx in txs]
        spread = max(timestamps) - min(timestamps) if timestamps else 0
        total_volume = sum(tx.amount_usd for tx in txs)
        presence = self._presence_score(wallets, txs, spread)
        toxicity = self._calculate_cluster_toxicity_score(wallets, txs)
        quality = max(0.0, min(100.0, presence - toxicity * 0.6 + self._buy_pressure_score(txs) * 0.4))
        return ClusterMetrics(
            cluster_id=cluster_id,
            wallet_count=len(wallets),
            coordination_type=coord_type,
            first_activity_timestamp=min(timestamps) if timestamps else 0,
            last_activity_timestamp=max(timestamps) if timestamps else 0,
            avg_entry_time_spread_seconds=float(spread),
            total_volume_usd=total_volume,
            combined_trade_count=len(txs),
            confidence_score=presence,
            cluster_presence_score=presence,
            cluster_quality_score=quality,
            cluster_toxicity_score=toxicity,
            cluster_lead_time_score=self._calculate_cluster_lead_time_score(txs),
            cluster_exit_pressure_score=self._calculate_cluster_exit_pressure_score(txs),
            funding_source_similarity=self._calculate_funding_source_similarity(wallets),
            position_size_similarity=self._calculate_position_size_similarity(txs),
            route_similarity=self._calculate_route_similarity(txs),
        )

    def _classify_coordination_type(self, wallets: list[str], txs: list[TransactionEvent]) -> CoordinationType:
        if not txs:
            return CoordinationType.UNKNOWN
        buys = [tx for tx in txs if tx.side.lower() == "buy"]
        sells = [tx for tx in txs if tx.side.lower() == "sell"]
        by_token: dict[str, list[int]] = defaultdict(list)
        for tx in buys:
            by_token[tx.token_mint].append(tx.timestamp)
        for stamps in by_token.values():
            if len(stamps) >= len(wallets) and max(stamps) - min(stamps) <= 30:
                return CoordinationType.SIMULTANEOUS_ENTRY
            if len(stamps) >= 2:
                sorted_stamps = sorted(stamps)
                diffs = [b - a for a, b in zip(sorted_stamps, sorted_stamps[1:])]
                if diffs and mean(diffs) <= 120:
                    return CoordinationType.SEQUENTIAL_ENTRY
        if sells and sum(tx.amount_usd for tx in sells) > sum(tx.amount_usd for tx in buys) * 0.7:
            return CoordinationType.ANTAGONISTIC
        if buys and len(buys) >= len(wallets) * 2 and max(tx.timestamp for tx in buys) - min(tx.timestamp for tx in buys) <= 300:
            return CoordinationType.PUMP_COORDINATION
        return CoordinationType.DISTRIBUTED_COORDINATION

    def detect_pre_cluster_signals(self, token: str, current_wallets: set[str]) -> list[PreClusterSignal]:
        # New wallets without observed history are not a signal. They are UNKNOWN.
        observable_new_wallets = [w for w in current_wallets if w not in self.wallet_profiles and self.transaction_history.get(w)]
        signals: list[PreClusterSignal] = []
        if len(observable_new_wallets) >= 2:
            txs = [tx for w in observable_new_wallets for tx in self.transaction_history[w][-10:]]
            if len(txs) >= 2:
                spread = max(tx.timestamp for tx in txs) - min(tx.timestamp for tx in txs)
                if spread <= self.temporal_window:
                    signals.append(PreClusterSignal(
                        detected_at=max(tx.timestamp for tx in txs),
                        token_mint=token,
                        wallets_involved=observable_new_wallets,
                        trigger_type="observable_new_wallet_temporal_proximity",
                        confidence_score=max(0.0, 100.0 - spread / max(1, self.temporal_window) * 100.0),
                        notes="new wallets have local tx history; no invisible history was assumed",
                    ))
        return signals

    def _presence_score(self, wallets: list[str], txs: list[TransactionEvent], spread: int) -> float:
        wallet_score = min(40.0, len(wallets) * 10.0)
        spread_score = max(0.0, 40.0 - spread / max(1, self.temporal_window) * 40.0)
        activity_score = min(20.0, len(txs) * 2.0)
        return min(100.0, wallet_score + spread_score + activity_score)

    def _buy_pressure_score(self, txs: list[TransactionEvent]) -> float:
        buy = sum(tx.amount_usd for tx in txs if tx.side.lower() == "buy")
        sell = sum(tx.amount_usd for tx in txs if tx.side.lower() == "sell")
        return max(0.0, min(100.0, (buy - sell) / max(1.0, buy + sell) * 50.0 + 50.0))

    def _calculate_cluster_toxicity_score(self, wallets: list[str], txs: list[TransactionEvent]) -> float:
        if not txs:
            return 0.0
        sell_pressure = self._calculate_cluster_exit_pressure_score(txs)
        size_similarity = self._calculate_position_size_similarity(txs) * 25.0
        route_similarity = self._calculate_route_similarity(txs) * 15.0
        funding_similarity = self._calculate_funding_source_similarity(wallets) * 30.0
        same_token_penalty = 15.0 if len({tx.token_mint for tx in txs}) <= 1 and len(txs) >= len(wallets) else 0.0
        return min(100.0, sell_pressure * 0.4 + size_similarity + route_similarity + funding_similarity + same_token_penalty)

    def _calculate_cluster_lead_time_score(self, txs: list[TransactionEvent]) -> float:
        if len(txs) < 2:
            return 0.0
        spread = max(tx.timestamp for tx in txs) - min(tx.timestamp for tx in txs)
        return max(0.0, min(100.0, 100.0 - spread / max(1, self.temporal_window) * 100.0))

    def _calculate_cluster_exit_pressure_score(self, txs: list[TransactionEvent]) -> float:
        total = sum(tx.amount_usd for tx in txs)
        sells = sum(tx.amount_usd for tx in txs if tx.side.lower() == "sell")
        return min(100.0, sells / max(1.0, total) * 100.0)

    def _calculate_funding_source_similarity(self, wallets: list[str]) -> float:
        sources = [self.wallet_profiles[w].associated_addresses for w in wallets if w in self.wallet_profiles]
        if len(sources) < 2:
            return 0.0
        scores: list[float] = []
        for i, a in enumerate(sources):
            for b in sources[i + 1:]:
                scores.append(len(a & b) / max(1, len(a | b)))
        return mean(scores) if scores else 0.0

    def _calculate_position_size_similarity(self, txs: list[TransactionEvent]) -> float:
        amounts = [tx.amount_usd for tx in txs if tx.amount_usd > 0]
        if len(amounts) < 2:
            return 0.0
        m = mean(amounts)
        cv = pstdev(amounts) / max(1.0, m)
        return max(0.0, min(1.0, 1.0 - cv))

    def _calculate_route_similarity(self, txs: list[TransactionEvent]) -> float:
        if len(txs) < 2:
            return 0.0
        counts: dict[str, int] = defaultdict(int)
        for tx in txs:
            counts[tx.route or tx.dex] += 1
        return max(counts.values()) / len(txs)

#!/usr/bin/env python3
"""Build wallet-derived cluster context rows for entry points.

This stage is intentionally conservative. It uses only local CSV artifacts and
never turns cluster presence into an alpha claim. If market-wide wallet data is
not available, rows are written as UNKNOWN instead of fabricating cluster data.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from advanced_coordinated_wallet_detector import ClusterMetrics, CoordinatedWalletDetector, TransactionEvent
from common import DATA_PROCESSED, TARGET_WALLET, as_float, as_int, ensure_dirs, read_csv, write_csv

UNKNOWN = "UNKNOWN"
FIELDNAMES = [
    "entry_signature",
    "token_mint",
    "entry_time",
    "entry_slot",
    "context_window_seconds",
    "cluster_id",
    "cluster_wallet_count_30s",
    "cluster_temporal_spread_seconds",
    "coordination_type",
    "cluster_presence_score",
    "cluster_quality_score",
    "cluster_toxicity_score",
    "cluster_lead_time_score",
    "cluster_exit_pressure_score",
    "funding_source_similarity",
    "position_size_similarity",
    "route_similarity",
    "context_status",
    "coverage_source",
    "notes",
]


def wallet_of(row: dict[str, str]) -> str:
    return row.get("wallet") or row.get("owner") or row.get("trader") or row.get("signer") or TARGET_WALLET


def side_of(row: dict[str, str]) -> str:
    return (row.get("side") or row.get("direction") or "").lower()


def amount_usd(row: dict[str, str]) -> float:
    if row.get("amount_usd") not in (None, ""):
        return as_float(row.get("amount_usd"))
    if row.get("sol_amount") not in (None, ""):
        return as_float(row.get("sol_amount")) * as_float(row.get("sol_price_usd"), 0.0)
    return as_float(row.get("amount"), 0.0)


def amount_tokens(row: dict[str, str]) -> float:
    return as_float(row.get("token_amount"), as_float(row.get("amount_tokens"), 0.0))


def price_usd(row: dict[str, str]) -> float:
    if row.get("price_usd") not in (None, ""):
        return as_float(row.get("price_usd"))
    return as_float(row.get("price_sol"), 0.0) * as_float(row.get("sol_price_usd"), 0.0)


def row_time(row: dict[str, str]) -> int:
    return as_int(row.get("block_time") or row.get("timestamp") or row.get("time"), 0)


def row_slot(row: dict[str, str]) -> int:
    return as_int(row.get("slot"), 0)


def is_before(row: dict[str, str], entry_time: int, entry_slot: int, entry_signature: str) -> bool:
    if entry_signature and row.get("signature") == entry_signature:
        return False
    timestamp = row_time(row)
    slot = row_slot(row)
    if timestamp <= 0 or entry_time <= 0:
        return False
    return timestamp < entry_time or (timestamp == entry_time and slot > 0 and entry_slot > 0 and slot < entry_slot)


def to_event(row: dict[str, str]) -> TransactionEvent:
    return TransactionEvent(
        tx_hash=row.get("signature", ""),
        wallet=wallet_of(row),
        token_mint=row.get("token_mint", ""),
        side=side_of(row),
        amount_usd=amount_usd(row),
        amount_tokens=amount_tokens(row),
        price_usd=price_usd(row),
        timestamp=row_time(row),
        slot=row_slot(row),
        block=as_int(row.get("block"), row_slot(row)),
        dex=row.get("dex") or row.get("program") or "unknown",
        gas_fee_lamports=as_int(row.get("fee_lamports"), 0),
        priority_fee_lamports=as_int(row.get("priority_fee_lamports"), 0),
        route=row.get("route", ""),
        funding_source=row.get("funding_source", ""),
    )


def empty_row(entry: dict[str, str], window: int, reason: str) -> dict[str, Any]:
    return {
        "entry_signature": entry.get("entry_signature", ""),
        "token_mint": entry.get("token_mint", ""),
        "entry_time": entry.get("entry_time", ""),
        "entry_slot": entry.get("entry_slot", ""),
        "context_window_seconds": window,
        "cluster_id": "",
        "cluster_wallet_count_30s": "",
        "cluster_temporal_spread_seconds": "",
        "coordination_type": UNKNOWN,
        "cluster_presence_score": "",
        "cluster_quality_score": "",
        "cluster_toxicity_score": "",
        "cluster_lead_time_score": "",
        "cluster_exit_pressure_score": "",
        "funding_source_similarity": "",
        "position_size_similarity": "",
        "route_similarity": "",
        "context_status": UNKNOWN,
        "coverage_source": "wallet_swaps",
        "notes": reason,
    }


def metric_row(entry: dict[str, str], window: int, metric: ClusterMetrics) -> dict[str, Any]:
    return {
        "entry_signature": entry.get("entry_signature", ""),
        "token_mint": entry.get("token_mint", ""),
        "entry_time": entry.get("entry_time", ""),
        "entry_slot": entry.get("entry_slot", ""),
        "context_window_seconds": window,
        "cluster_id": metric.cluster_id,
        "cluster_wallet_count_30s": metric.wallet_count,
        "cluster_temporal_spread_seconds": metric.avg_entry_time_spread_seconds,
        "coordination_type": metric.coordination_type.value,
        "cluster_presence_score": f"{metric.cluster_presence_score:.6f}",
        "cluster_quality_score": f"{metric.cluster_quality_score:.6f}",
        "cluster_toxicity_score": f"{metric.cluster_toxicity_score:.6f}",
        "cluster_lead_time_score": f"{metric.cluster_lead_time_score:.6f}",
        "cluster_exit_pressure_score": f"{metric.cluster_exit_pressure_score:.6f}",
        "funding_source_similarity": f"{metric.funding_source_similarity:.6f}",
        "position_size_similarity": f"{metric.position_size_similarity:.6f}",
        "route_similarity": f"{metric.route_similarity:.6f}",
        "context_status": "PARTIAL",
        "coverage_source": "wallet_swaps",
        "notes": "wallet-derived cluster context; validate against controls before any alpha claim",
    }


def build_cluster_context(
    entries: list[dict[str, str]],
    swaps: list[dict[str, str]],
    window: int = 300,
    min_wallets: int = 3,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in entries:
        mint = entry.get("token_mint", "")
        entry_time = as_int(entry.get("entry_time"), 0)
        entry_slot = as_int(entry.get("entry_slot"), 0)
        entry_signature = entry.get("entry_signature", "")
        candidates = [
            row
            for row in swaps
            if row.get("token_mint") == mint
            and is_before(row, entry_time, entry_slot, entry_signature)
            and row_time(row) >= entry_time - window
        ]
        wallets = {wallet_of(row) for row in candidates}
        if len(wallets) < min_wallets:
            rows.append(empty_row(entry, window, f"insufficient distinct wallets: {len(wallets)} < {min_wallets}"))
            continue
        detector = CoordinatedWalletDetector(temporal_window_seconds=window, cluster_size_min=min_wallets, cooccurrence_threshold=1)
        for row in candidates:
            detector.add_transaction(to_event(row))
        clusters = detector.detect_clusters()
        if not clusters:
            rows.append(empty_row(entry, window, "no cluster detected"))
            continue
        best = max(clusters.values(), key=lambda metric: metric.cluster_quality_score - metric.cluster_toxicity_score)
        rows.append(metric_row(entry, window, best))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Build cluster_context.csv from entry context and local swaps")
    parser.add_argument("--entry-context", default=str(DATA_PROCESSED / "entry_context.csv"))
    parser.add_argument("--swaps", default=str(DATA_PROCESSED / "wallet_swaps.csv"))
    parser.add_argument("--output", default=str(DATA_PROCESSED / "cluster_context.csv"))
    parser.add_argument("--window-seconds", type=int, default=300)
    parser.add_argument("--min-wallets", type=int, default=3)
    args = parser.parse_args()

    ensure_dirs()
    rows = build_cluster_context(read_csv(Path(args.entry_context)), read_csv(Path(args.swaps)), args.window_seconds, args.min_wallets)
    write_csv(Path(args.output), rows, FIELDNAMES)
    print(f"[OK] wrote {len(rows)} cluster context rows to {args.output}")


if __name__ == "__main__":
    main()

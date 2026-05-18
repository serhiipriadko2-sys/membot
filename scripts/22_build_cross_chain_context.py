#!/usr/bin/env python3
"""Build cross-chain regime context rows for entries.

Cross-chain context is a regime filter, not a token-specific BUY trigger. Missing
event data remains UNKNOWN.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from common import DATA_PROCESSED, as_float, as_int, ensure_dirs, read_csv, write_csv
from cross_chain_sentiment_monitor import ActivityType, Chain, CrossChainEvent, CrossChainMonitor

UNKNOWN = "UNKNOWN"
FIELDNAMES = [
    "entry_signature",
    "token_mint",
    "entry_time",
    "entry_slot",
    "target_chain",
    "context_window_seconds",
    "combined_momentum",
    "signal_count",
    "recommendation",
    "bridge_inflow_usd_15m",
    "bridge_outflow_usd_15m",
    "cross_chain_attention_delta",
    "context_status",
    "coverage_source",
    "notes",
]


def parse_chain(value: str) -> Chain:
    try:
        return Chain((value or "").lower())
    except ValueError:
        return Chain.ETHEREUM


def parse_activity(value: str) -> ActivityType:
    try:
        return ActivityType((value or "").lower())
    except ValueError:
        return ActivityType.LARGE_TRANSFER


def event_time(row: dict[str, str]) -> int:
    return as_int(row.get("timestamp") or row.get("block_time") or row.get("time"), 0)


def to_event(row: dict[str, str]) -> CrossChainEvent:
    return CrossChainEvent(
        event_id=row.get("event_id") or row.get("signature") or f"event-{event_time(row)}",
        chain=parse_chain(row.get("chain", "ethereum")),
        event_type=parse_activity(row.get("event_type", "large_transfer")),
        timestamp=event_time(row),
        block_number=as_int(row.get("block_number") or row.get("block"), 0),
        token_address=row.get("token_address") or row.get("token_mint") or "",
        amount_usd=as_float(row.get("amount_usd"), 0.0),
        amount_native=as_float(row.get("amount_native"), 0.0),
        actor_address=row.get("actor_address") or row.get("wallet") or "",
        token_symbol=row.get("token_symbol") or row.get("symbol") or None,
        actor_label=row.get("actor_label") or None,
    )


def empty_row(entry: dict[str, str], window: int, reason: str) -> dict[str, Any]:
    return {
        "entry_signature": entry.get("entry_signature", ""),
        "token_mint": entry.get("token_mint", ""),
        "entry_time": entry.get("entry_time", ""),
        "entry_slot": entry.get("entry_slot", ""),
        "target_chain": "solana",
        "context_window_seconds": window,
        "combined_momentum": "",
        "signal_count": 0,
        "recommendation": UNKNOWN,
        "bridge_inflow_usd_15m": "",
        "bridge_outflow_usd_15m": "",
        "cross_chain_attention_delta": "",
        "context_status": UNKNOWN,
        "coverage_source": "cross_chain_events",
        "notes": reason,
    }


def build_cross_chain_context(entries: list[dict[str, str]], events: list[dict[str, str]], window: int = 900) -> list[dict[str, Any]]:
    parsed = [to_event(event) for event in events if event_time(event) > 0]
    rows: list[dict[str, Any]] = []
    for entry in entries:
        entry_time = as_int(entry.get("entry_time"), 0)
        if entry_time <= 0:
            rows.append(empty_row(entry, window, "entry_time missing"))
            continue
        subset = [event for event in parsed if entry_time - window <= event.timestamp < entry_time]
        if not subset:
            rows.append(empty_row(entry, window, "no cross-chain events in pre-entry window"))
            continue
        monitor = CrossChainMonitor(now=entry_time)
        monitor.add_event_batch(subset)
        signal = monitor.detect_leading_signals(Chain.SOLANA)
        bridge_inflow = sum(event.amount_usd for event in subset if event.event_type == ActivityType.BRIDGE_FLOW and event.chain != Chain.SOLANA)
        bridge_outflow = sum(event.amount_usd for event in subset if event.event_type == ActivityType.BRIDGE_FLOW and event.chain == Chain.SOLANA)
        attention = sum(event.amount_usd for event in subset if event.event_type in {ActivityType.DEX_VOLUME_SPIKE, ActivityType.NEW_TOKEN_LAUNCH})
        rows.append({
            "entry_signature": entry.get("entry_signature", ""),
            "token_mint": entry.get("token_mint", ""),
            "entry_time": entry.get("entry_time", ""),
            "entry_slot": entry.get("entry_slot", ""),
            "target_chain": signal.get("target_chain", "solana"),
            "context_window_seconds": window,
            "combined_momentum": f"{float(signal.get('combined_momentum', 0.0)):.6f}",
            "signal_count": signal.get("signal_count", 0),
            "recommendation": signal.get("recommendation", UNKNOWN),
            "bridge_inflow_usd_15m": f"{bridge_inflow:.6f}",
            "bridge_outflow_usd_15m": f"{bridge_outflow:.6f}",
            "cross_chain_attention_delta": f"{attention:.6f}",
            "context_status": "PARTIAL",
            "coverage_source": "cross_chain_events",
            "notes": "regime context only; not token-specific BUY evidence",
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Build cross_chain_context.csv from local event export")
    parser.add_argument("--entry-context", default=str(DATA_PROCESSED / "entry_context.csv"))
    parser.add_argument("--events", default=str(DATA_PROCESSED / "cross_chain_events.csv"))
    parser.add_argument("--output", default=str(DATA_PROCESSED / "cross_chain_context.csv"))
    parser.add_argument("--window-seconds", type=int, default=900)
    args = parser.parse_args()

    ensure_dirs()
    rows = build_cross_chain_context(read_csv(Path(args.entry_context)), read_csv(Path(args.events)), args.window_seconds)
    write_csv(Path(args.output), rows, FIELDNAMES)
    print(f"[OK] wrote {len(rows)} cross-chain context rows to {args.output}")


if __name__ == "__main__":
    main()

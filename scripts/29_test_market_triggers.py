#!/usr/bin/env python3
"""Validate market-wide context against matched controls.

This script tests whether market-wide pre-entry context separates target wallet
entries from market/control anchors. It does not claim a tradable trigger without
OOS, latency, fee, and slippage validation.
"""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path
from typing import Any

from common import DATA_PROCESSED, REPORTS, ensure_dirs, read_csv, write_csv

trigger_tests = importlib.import_module("20_test_entry_triggers")

DEFAULT_MARKET_FEATURES = [
    {"feature_id": "market_tx_count_30s", "family": "market_microstructure", "source": "market_context", "direction": "higher", "feature_role": "trading_trigger"},
    {"feature_id": "market_volume_usd_30s", "family": "market_microstructure", "source": "market_context", "direction": "higher", "feature_role": "trading_trigger"},
    {"feature_id": "market_buy_count_30s", "family": "market_microstructure", "source": "market_context", "direction": "higher", "feature_role": "trading_trigger"},
    {"feature_id": "market_sell_count_30s", "family": "market_microstructure", "source": "market_context", "direction": "lower", "feature_role": "trading_trigger"},
    {"feature_id": "market_buy_sell_imbalance_30s", "family": "market_microstructure", "source": "market_context", "direction": "higher", "feature_role": "trading_trigger"},
    {"feature_id": "market_unique_buyers_30s", "family": "market_microstructure", "source": "market_context", "direction": "higher", "feature_role": "trading_trigger"},
    {"feature_id": "market_unique_sellers_30s", "family": "market_microstructure", "source": "market_context", "direction": "lower", "feature_role": "trading_trigger"},
    {"feature_id": "market_price_change_30s", "family": "market_price_action", "source": "market_context", "direction": "higher", "feature_role": "trading_trigger"},
    {"feature_id": "market_tx_rate_30s", "family": "market_microstructure", "source": "market_context", "direction": "higher", "feature_role": "trading_trigger"},
]


def split_market_context(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    entries = [row for row in rows if row.get("anchor_type") == "entry"]
    controls = [row for row in rows if row.get("anchor_type") != "entry"]
    return entries, controls


def build_market_trigger_tests(
    market_context_rows: list[dict[str, str]],
    features: list[dict[str, str]] | None = None,
    bootstrap_iters: int = 300,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    entry_rows, control_rows = split_market_context(market_context_rows)
    return trigger_tests.build_trigger_tests(
        entry_rows=entry_rows,
        control_rows=control_rows,
        features=features or DEFAULT_MARKET_FEATURES,
        bootstrap_iters=bootstrap_iters,
        top_k=top_k,
    )


def render_market_report(rows: list[dict[str, Any]], entry_count: int, control_count: int) -> str:
    base = trigger_tests.render_report(rows, entry_count, control_count)
    return base + "\n## Market-wide guardrail\n\nA PASS here means entry-vs-control separation in the supplied local market export only. It is not a trading signal until OOS, latency, fee, and slippage checks pass. Dune/DEX rows may include multi-hop components and must be grouped carefully for final trade-count claims.\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Test market-wide context against control anchors")
    parser.add_argument("--market-context", default=str(DATA_PROCESSED / "market_context.csv"))
    parser.add_argument("--output", default=str(DATA_PROCESSED / "market_trigger_tests.csv"))
    parser.add_argument("--report", default=str(REPORTS / "market_trigger_report.md"))
    parser.add_argument("--bootstrap-iters", type=int, default=300)
    parser.add_argument("--top-k", type=int, default=10)
    args = parser.parse_args()

    ensure_dirs()
    market_rows = read_csv(Path(args.market_context))
    entry_rows, control_rows = split_market_context(market_rows)
    rows = build_market_trigger_tests(market_rows, DEFAULT_MARKET_FEATURES, args.bootstrap_iters, args.top_k)
    write_csv(Path(args.output), rows, trigger_tests.TEST_FIELDNAMES)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_market_report(rows, len(entry_rows), len(control_rows)), encoding="utf-8")
    print(f"[OK] wrote {len(rows)} market trigger tests to {args.output}")


if __name__ == "__main__":
    main()

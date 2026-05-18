#!/usr/bin/env python3
"""Write a first-pass metrics report with explicit unknowns."""

from __future__ import annotations

import argparse
from collections import defaultdict
from statistics import median

from common import DATA_PROCESSED, DATA_RAW, REPORTS, as_float, ensure_dirs, read_csv, read_json


def count_json_items(path):
    payload = read_json(path, default={})
    if isinstance(payload, dict):
        return int(payload.get("count") or len(payload.get("items", [])))
    if isinstance(payload, list):
        return len(payload)
    return 0


def pct(n: int, d: int) -> str:
    if d <= 0:
        return "UNKNOWN"
    return f"{(n / d) * 100:.2f}%"


def bucket_hold(seconds: int) -> str:
    if seconds < 60:
        return "<1m"
    if seconds < 300:
        return "1m-5m"
    if seconds < 900:
        return "5m-15m"
    if seconds < 3600:
        return "15m-1h"
    return ">=1h"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build metrics report from processed artifacts")
    parser.add_argument("--output", default=str(REPORTS / "metrics_report.md"))
    args = parser.parse_args()

    ensure_dirs()
    signatures_n = count_json_items(DATA_RAW / "signatures_raw.json")
    transactions_n = count_json_items(DATA_RAW / "transactions_raw.json")
    swaps = read_csv(DATA_PROCESSED / "wallet_swaps.csv")
    trades = read_csv(DATA_PROCESSED / "trades_paired.csv")
    price_series = read_csv(DATA_PROCESSED / "price_series.csv")
    latency = read_csv(DATA_PROCESSED / "latency_sim.csv")

    parsed_swaps = [r for r in swaps if r.get("side") in {"BUY", "SELL"}]
    pnls = [as_float(t.get("net_pnl_sol"), as_float(t.get("pnl_sol"))) for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = f"{gross_profit / gross_loss:.6f}" if gross_loss > 0 else "UNKNOWN"
    holds = [int(float(t.get("hold_seconds") or 0)) for t in trades if t.get("hold_seconds") not in (None, "")]
    median_hold = str(median(holds)) if holds else "UNKNOWN"

    hold_buckets = defaultdict(lambda: {"n": 0, "pnl": 0.0})
    for trade in trades:
        if trade.get("hold_seconds") in (None, ""):
            continue
        bucket = bucket_hold(int(float(trade.get("hold_seconds") or 0)))
        hold_buckets[bucket]["n"] += 1
        hold_buckets[bucket]["pnl"] += as_float(trade.get("net_pnl_sol"), as_float(trade.get("pnl_sol")))

    h3 = "UNKNOWN"
    if price_series and latency:
        valid_3s = [row for row in latency if row.get("status_3s") == "valid"]
        if valid_3s:
            h3 = "PARTIAL"

    lines = []
    lines.append("# Metrics Report")
    lines.append("")
    lines.append("## Coverage")
    lines.append(f"- signatures_fetched: {signatures_n}")
    lines.append(f"- transactions_fetched: {transactions_n}")
    lines.append(f"- parsed_swaps: {len(parsed_swaps)}")
    lines.append(f"- paired_trades: {len(trades)}")
    lines.append(f"- price_points: {len(price_series)}")
    lines.append(f"- latency_rows: {len(latency)}")
    lines.append("")
    lines.append("## Core metrics")
    lines.append(f"- win_rate: {pct(len(wins), len(pnls))}")
    lines.append(f"- profit_factor: {profit_factor}")
    lines.append(f"- median_hold_seconds: {median_hold}")
    lines.append(f"- gross_profit_sol: {gross_profit}")
    lines.append(f"- gross_loss_sol: {gross_loss}")
    lines.append(f"- net_pnl_sol: {sum(pnls)}")
    lines.append("")
    lines.append("## PnL by hold bucket")
    if hold_buckets:
        for label in ["<1m", "1m-5m", "5m-15m", "15m-1h", ">=1h"]:
            bucket = hold_buckets.get(label)
            if not bucket:
                continue
            lines.append(f"- {label}: n={bucket['n']}, pnl_sol={bucket['pnl']}")
    else:
        lines.append("- UNKNOWN: no paired trades yet")
    lines.append("")
    lines.append("## Hypotheses status")
    lines.append(f"- H1 short-horizon scalper: {'PARTIAL' if holds else 'UNKNOWN'}")
    lines.append("- H2 ultra-small-cap edge: UNKNOWN until entry context enrichment exists")
    lines.append(f"- H3 execution edge latency decay: {h3}")
    lines.append("- H4 event-triggered entries: UNKNOWN until control-point study exists")
    lines.append("")
    lines.append("## Notes")
    lines.append("- price_series.csv is wallet-derived unless a stronger source is added.")
    lines.append("- H3 must remain UNKNOWN when price coverage is absent or too thin.")
    lines.append("- No algorithm claim should be made from this report alone.")

    __import__("pathlib").Path(args.output).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[OK] wrote report to {args.output}")


if __name__ == "__main__":
    main()

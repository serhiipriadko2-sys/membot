#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from common import DATA_PROCESSED, REPORTS, as_float, ensure_dirs, read_csv

MANDATORY = [
    "This report is not a trading recommendation.",
    "This report does not prove the wallet algorithm.",
    "Copy-stress model is not latency replay.",
    "Latency replay is UNKNOWN unless price_series.csv exists.",
]

def sum_col(rows: list[dict[str, str]], col: str) -> float:
    return sum(as_float(r.get(col)) for r in rows)

def scenario_summary(rows: list[dict[str, str]]) -> list[tuple[str, int, float, float]]:
    grouped: dict[str, list[float]] = {}
    for row in rows:
        grouped.setdefault(row.get("scenario", "UNKNOWN"), []).append(as_float(row.get("copy_net_pnl_usd")))
    out: list[tuple[str, int, float, float]] = []
    for scenario, vals in sorted(grouped.items()):
        winrate = sum(1 for v in vals if v > 0) / len(vals) if vals else 0.0
        out.append((scenario, len(vals), sum(vals), winrate))
    return out

def generate_report(processed_dir: Path = DATA_PROCESSED) -> str:
    swaps = read_csv(processed_dir / "wallet_swaps.csv")
    paired = read_csv(processed_dir / "trades_paired.csv")
    fee_rows = read_csv(processed_dir / "fee_adjusted_pnl.csv")
    stress = read_csv(processed_dir / "copy_stress_model.csv")
    price_series_exists = (processed_dir / "price_series.csv").exists()
    low_conf = sum(1 for r in swaps if str(r.get("parse_confidence", "")).lower().startswith("low"))
    n_input = len(swaps)
    n_paired = len(paired) or len(fee_rows)
    coverage_pct = (n_paired / n_input * 100) if n_input else 0.0
    gross = sum_col(fee_rows, "gross_pnl_usd")
    fees = sum_col(fee_rows, "observed_fee_usd")
    net = sum_col(fee_rows, "net_pnl_usd")
    missing_fee = sum(1 for r in fee_rows if r.get("fee_confidence") == "low_missing_observed_fee")

    lines: list[str] = ["# Backtest report", ""]
    lines.extend(f"- {text}" for text in MANDATORY)
    lines.extend([
        "", "## Coverage",
        f"- N input rows: {n_input}",
        f"- N normalized swaps: {len(swaps)}",
        f"- N paired trades: {n_paired}",
        "- N unpaired buys: UNKNOWN unless pairing audit is implemented",
        "- N unpaired sells: UNKNOWN unless pairing audit is implemented",
        f"- N low-confidence rows: {low_conf}",
        f"- coverage_pct: {coverage_pct:.2f}%",
        "", "## Observed fee-adjusted PnL",
        f"- observed_gross_pnl_usd: {gross:.6f}",
        f"- observed_fees_usd: {fees:.6f}",
        f"- observed_net_pnl_usd: {net:.6f}",
        f"- rows_missing_observed_fee: {missing_fee}",
        "", "## Copy-stress scenarios",
        "| scenario | rows | total_copy_net_pnl_usd | winrate |",
        "|---|---:|---:|---:|",
    ])
    for scenario, count, total, winrate in scenario_summary(stress):
        lines.append(f"| {scenario} | {count} | {total:.6f} | {winrate:.2%} |")
    if not stress:
        lines.append("| UNKNOWN_no_copy_stress_model | 0 | 0.000000 | 0.00% |")
    latency_status = "AVAILABLE" if price_series_exists else "UNKNOWN"
    lines.extend(["", "## Latency replay", f"latency_replay_status: {latency_status}", "", "## Limitations", "- Dashboard metrics are not raw SoT.", "- Copy-stress scenarios are formulaic stress tests, not true delayed-entry backtests.", "- True latency replay requires `price_series.csv` with delayed-entry prices."])
    return "\n".join(lines) + "\n"

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    ensure_dirs()
    output = Path(args.output) if args.output else REPORTS / "backtest_report.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(generate_report(), encoding="utf-8")
    print(f"[OK] wrote backtest report to {output}")

if __name__ == "__main__":
    main()

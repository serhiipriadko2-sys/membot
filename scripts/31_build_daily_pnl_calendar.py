#!/usr/bin/env python3
"""Build a daily realized PnL calendar from paired FIFO trades.

This script is a raw-replay guardrail for dashboard PnL calendars:
- it uses paired trades, grouped by exit date UTC;
- it reports gross/net PnL, fees, win rate, and coverage;
- it does not treat dashboard green days as truth.

Default outputs:
- data/processed/daily_pnl_calendar.csv
- reports/daily_pnl_calendar_report.md
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from common import DATA_PROCESSED, REPORTS, as_float, as_int, ensure_dirs, read_csv, write_csv

FIELDS = [
    "date_utc",
    "trade_count",
    "winning_trades",
    "losing_trades",
    "flat_trades",
    "win_rate_pct",
    "gross_pnl_sol",
    "fees_sol",
    "net_pnl_sol",
    "avg_net_pnl_sol",
    "best_trade_net_pnl_sol",
    "worst_trade_net_pnl_sol",
    "is_green_day",
    "source_coverage",
    "notes",
]


def parse_epoch(value: Any) -> int:
    return as_int(value, 0)


def date_from_epoch(value: Any) -> str:
    ts = parse_epoch(value)
    if ts <= 0:
        return "UNKNOWN"
    return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()


def net_pnl(row: dict[str, str]) -> float:
    if row.get("net_pnl_sol") not in (None, ""):
        return as_float(row.get("net_pnl_sol"), 0.0)
    pnl = as_float(row.get("pnl_sol"), 0.0)
    fees = as_float(row.get("fees_sol"), 0.0)
    return pnl - fees


def fees(row: dict[str, str]) -> float:
    return as_float(row.get("fees_sol"), 0.0)


def build_daily(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[date_from_epoch(row.get("exit_time") or row.get("block_time") or row.get("timestamp"))].append(row)

    out: list[dict[str, Any]] = []
    for day in sorted(grouped):
        trades = grouped[day]
        values = [net_pnl(row) for row in trades]
        gross_values = [as_float(row.get("pnl_sol"), net_pnl(row)) for row in trades]
        fee_values = [fees(row) for row in trades]
        wins = sum(1 for value in values if value > 0)
        losses = sum(1 for value in values if value < 0)
        flats = len(values) - wins - losses
        total_net = sum(values)
        total_gross = sum(gross_values)
        total_fees = sum(fee_values)
        fee_known = sum(1 for row in trades if row.get("fees_sol") not in (None, ""))
        if day == "UNKNOWN":
            coverage = "missing_time"
        elif fee_known == len(trades):
            coverage = "pnl_and_fees"
        elif fee_known > 0:
            coverage = "partial_fees"
        else:
            coverage = "pnl_only_no_fee_column"
        out.append(
            {
                "date_utc": day,
                "trade_count": len(trades),
                "winning_trades": wins,
                "losing_trades": losses,
                "flat_trades": flats,
                "win_rate_pct": f"{(wins / len(trades) * 100) if trades else 0:.2f}",
                "gross_pnl_sol": f"{total_gross:.12f}",
                "fees_sol": f"{total_fees:.12f}",
                "net_pnl_sol": f"{total_net:.12f}",
                "avg_net_pnl_sol": f"{(total_net / len(trades)) if trades else 0:.12f}",
                "best_trade_net_pnl_sol": f"{max(values) if values else 0:.12f}",
                "worst_trade_net_pnl_sol": f"{min(values) if values else 0:.12f}",
                "is_green_day": "true" if total_net > 0 else "false",
                "source_coverage": coverage,
                "notes": "realized FIFO grouped by exit_time UTC; dashboard PnL not used",
            }
        )
    return out


def longest_green_streak(days: list[dict[str, Any]]) -> int:
    best = 0
    current = 0
    for row in days:
        if row.get("date_utc") == "UNKNOWN":
            continue
        if str(row.get("is_green_day", "")).lower() == "true":
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def render_report(rows: list[dict[str, Any]], trade_count: int, input_path: Path) -> str:
    known_days = [row for row in rows if row.get("date_utc") != "UNKNOWN"]
    green_days = [row for row in known_days if str(row.get("is_green_day", "")).lower() == "true"]
    red_days = [row for row in known_days if str(row.get("is_green_day", "")).lower() != "true"]
    total_net = sum(as_float(row.get("net_pnl_sol"), 0.0) for row in rows)
    total_gross = sum(as_float(row.get("gross_pnl_sol"), 0.0) for row in rows)
    total_fees = sum(as_float(row.get("fees_sol"), 0.0) for row in rows)
    lines = [
        "# Daily PnL Calendar Report",
        "",
        "## Scope",
        "",
        f"- Input: `{input_path}`",
        f"- Paired trade rows: `{trade_count}`",
        f"- Calendar rows: `{len(rows)}`",
        "- Grouping rule: realized FIFO trades grouped by `exit_time` UTC.",
        "- Guardrail: dashboard green-day claims are not used as source of truth.",
        "",
        "## Summary",
        "",
        f"- Known days: `{len(known_days)}`",
        f"- Green days: `{len(green_days)}`",
        f"- Red/flat days: `{len(red_days)}`",
        f"- Longest green streak: `{longest_green_streak(rows)}`",
        f"- Gross PnL SOL: `{total_gross:.6f}`",
        f"- Fees SOL: `{total_fees:.6f}`",
        f"- Net PnL SOL: `{total_net:.6f}`",
        "",
        "## Notes",
        "",
        "- If fee fields are blank, `net_pnl_sol` may equal gross `pnl_sol` from pairing.",
        "- To validate an external PnL calendar, compare it with this raw-replay calendar after expanding the sample window.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build daily PnL calendar from paired trades")
    parser.add_argument("--trades", default=str(DATA_PROCESSED / "trades_paired.csv"))
    parser.add_argument("--output", default=str(DATA_PROCESSED / "daily_pnl_calendar.csv"))
    parser.add_argument("--report", default=str(REPORTS / "daily_pnl_calendar_report.md"))
    args = parser.parse_args()

    ensure_dirs()
    input_path = Path(args.trades)
    trades = read_csv(input_path)
    rows = build_daily(trades)
    write_csv(Path(args.output), rows, FIELDS)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(rows, len(trades), input_path), encoding="utf-8")
    print(f"[OK] wrote {len(rows)} daily PnL rows to {args.output}")
    print(f"[OK] wrote report to {args.report}")


if __name__ == "__main__":
    main()

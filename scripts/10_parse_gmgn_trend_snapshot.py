"""Parse stored GMGN Trend snapshots into a candidate-universe CSV.

This script is deliberately conservative:
- it stores/copies the raw snapshot before parsing;
- it preserves ambiguous lower-card metrics as raw_metric_a...raw_metric_g;
- it never emits buy/sell/trading signals;
- it marks parse_confidence and parse_notes per row.

Supported first input format: JSON extraction with keys:
  source, extracted_at_context, tokens, metrics_by_order
Non-JSON text/html snapshots are stored raw and produce no parsed rows until a
separate DOM/text extractor is added.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

try:
    from common import DATA_PROCESSED, DATA_RAW, ensure_dirs, utc_now_iso, write_csv
except ModuleNotFoundError:  # pragma: no cover - test/local fallback
    import csv
    from datetime import datetime, timezone

    ROOT = Path(__file__).resolve().parents[1]
    DATA_RAW = ROOT / "data" / "raw"
    DATA_PROCESSED = ROOT / "data" / "processed"

    def utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def ensure_dirs() -> None:
        DATA_RAW.mkdir(parents=True, exist_ok=True)
        DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({name: row.get(name, "") for name in fieldnames})

FIELDNAMES = [
    "snapshot_id",
    "snapshot_ts",
    "source_page",
    "source_title",
    "chain",
    "section",
    "filter_windows",
    "rank",
    "token_name",
    "display_name_raw",
    "token_mint",
    "address_short",
    "age_raw",
    "age_seconds",
    "score_in_card",
    "market_cap_raw",
    "growth_raw",
    "ath_mc_raw",
    "liquidity_raw",
    "volume_1h_raw",
    "transactions_1h_raw",
    "buys_sells_raw",
    "buys_1h",
    "sells_1h",
    "holders_raw",
    "total_fees_raw",
    "has_x",
    "has_website",
    "has_telegram",
    "has_pump_fun",
    "has_meteora",
    "token_info_raw",
    "raw_metric_a",
    "raw_metric_b",
    "raw_metric_c",
    "raw_metric_d",
    "raw_metric_e",
    "raw_metric_f",
    "raw_metric_g",
    "parse_confidence",
    "parse_notes",
    "raw_source_path",
]

MINT_RE = re.compile(r"[1-9A-HJ-NP-Za-km-z]{32,44}(?:pump)?")


def stable_snapshot_id(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()[:16]


def load_json_if_possible(path: Path) -> tuple[dict[str, Any] | None, bytes]:
    raw = path.read_bytes()
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, raw
    if isinstance(obj, dict):
        return obj, raw
    return None, raw


def store_raw_snapshot(input_path: Path, snapshot_id: str, raw_root: Path | None = None) -> Path:
    raw_root = raw_root or DATA_RAW / "gmgn_trend_snapshots"
    raw_root.mkdir(parents=True, exist_ok=True)
    suffix = input_path.suffix or ".raw"
    target = raw_root / f"{snapshot_id}{suffix}"
    shutil.copyfile(input_path, target)
    return target


def age_to_seconds(age: Any) -> str:
    if age in (None, ""):
        return ""
    value = str(age).strip().lower()
    m = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)([smhd])", value)
    if not m:
        return ""
    amount = float(m.group(1))
    unit = m.group(2)
    multiplier = {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]
    return str(int(amount * multiplier))


def normalize_int_like(value: Any) -> str:
    if value in (None, ""):
        return ""
    text = str(value).strip().replace(",", "")
    mult = 1.0
    if text.lower().endswith("k"):
        mult = 1_000.0
        text = text[:-1]
    elif text.lower().endswith("m"):
        mult = 1_000_000.0
        text = text[:-1]
    try:
        return str(int(float(text) * mult))
    except ValueError:
        return str(value)


def split_buys_sells(value: Any) -> tuple[str, str]:
    if value in (None, ""):
        return "", ""
    parts = str(value).replace(",", "").split("/")
    if len(parts) != 2:
        return "", ""
    return parts[0].strip(), parts[1].strip()


def flatten_links(links: Any) -> list[str]:
    if not isinstance(links, dict):
        return []
    result: list[str] = []
    for value in links.values():
        if isinstance(value, list):
            result.extend(str(item) for item in value)
        elif value:
            result.append(str(value))
    return result


def extract_mint(token: dict[str, Any], links: list[str]) -> str:
    for key in ("mint", "token_mint", "address"):
        if token.get(key):
            return str(token[key]).strip()
    for url in links:
        if "/coin/" in url:
            candidate = url.rsplit("/coin/", 1)[-1].split("?", 1)[0].split("#", 1)[0]
            if candidate:
                return candidate
    joined = " ".join(links)
    matches = MINT_RE.findall(joined)
    return matches[0] if matches else ""


def metrics_by_order(snapshot: dict[str, Any]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for idx, item in enumerate(snapshot.get("metrics_by_order", []) or [], start=1):
        if not isinstance(item, dict):
            continue
        order = item.get("token_order", idx)
        try:
            order_int = int(order)
        except (TypeError, ValueError):
            order_int = idx
        out[order_int] = item
    return out


def parse_rows(snapshot: dict[str, Any], snapshot_id: str, raw_source_path: Path, snapshot_ts: str) -> list[dict[str, Any]]:
    source = snapshot.get("source", {}) if isinstance(snapshot.get("source"), dict) else {}
    context = snapshot.get("extracted_at_context", {}) if isinstance(snapshot.get("extracted_at_context"), dict) else {}
    tokens = snapshot.get("tokens", []) or []
    metrics_map = metrics_by_order(snapshot)
    notes = snapshot.get("notes", {}) if isinstance(snapshot.get("notes"), dict) else {}
    uncertainty = notes.get("uncertainty", []) if isinstance(notes.get("uncertainty"), list) else []

    rows: list[dict[str, Any]] = []
    for rank, token in enumerate(tokens, start=1):
        if not isinstance(token, dict):
            continue
        metrics = metrics_map.get(rank, {})
        links = flatten_links(token.get("links"))
        buys, sells = split_buys_sells(metrics.get("buys_sells"))
        token_mint = extract_mint(token, links)
        parse_notes: list[str] = []
        confidence = "high"
        if not token_mint:
            confidence = "medium"
            parse_notes.append("missing_token_mint")
        if not metrics:
            confidence = "medium" if confidence == "high" else "low"
            parse_notes.append("missing_metrics_block")
        if uncertainty:
            parse_notes.append("ambiguous_lower_metrics_preserved")
        if token.get("action"):
            parse_notes.append("source_action_ignored_not_signal")

        row = {
            "snapshot_id": snapshot_id,
            "snapshot_ts": snapshot_ts,
            "source_page": source.get("page", ""),
            "source_title": source.get("title", ""),
            "chain": source.get("chain", ""),
            "section": context.get("section", ""),
            "filter_windows": "|".join(str(x) for x in (context.get("time_filters", []) or [])),
            "rank": rank,
            "token_name": token.get("name", ""),
            "display_name_raw": token.get("display_name_raw", ""),
            "token_mint": token_mint,
            "address_short": token.get("address_short", ""),
            "age_raw": token.get("age", ""),
            "age_seconds": age_to_seconds(token.get("age")),
            "score_in_card": token.get("score_in_card", ""),
            "market_cap_raw": metrics.get("market_cap", ""),
            "growth_raw": metrics.get("growth", ""),
            "ath_mc_raw": metrics.get("ath_mc", ""),
            "liquidity_raw": metrics.get("liquidity", ""),
            "volume_1h_raw": metrics.get("volume_1h", ""),
            "transactions_1h_raw": normalize_int_like(metrics.get("transactions_1h", "")),
            "buys_sells_raw": metrics.get("buys_sells", ""),
            "buys_1h": buys,
            "sells_1h": sells,
            "holders_raw": metrics.get("holders", ""),
            "total_fees_raw": metrics.get("total_fees", ""),
            "has_x": str(any("x.com" in url or "twitter.com" in url for url in links)).lower(),
            "has_website": str(bool(token.get("links", {}).get("website") if isinstance(token.get("links"), dict) else False)).lower(),
            "has_telegram": str(any("t.me" in url or "telegram" in url.lower() for url in links)).lower(),
            "has_pump_fun": str(any("pump.fun" in url for url in links)).lower(),
            "has_meteora": str(any("meteora" in url.lower() for url in links)).lower(),
            "token_info_raw": metrics.get("token_info", ""),
            "raw_metric_a": metrics.get("metric_a", ""),
            "raw_metric_b": metrics.get("metric_b", ""),
            "raw_metric_c": metrics.get("metric_c", ""),
            "raw_metric_d": metrics.get("metric_d", ""),
            "raw_metric_e": metrics.get("metric_e", ""),
            "raw_metric_f": metrics.get("metric_f", ""),
            "raw_metric_g": metrics.get("metric_g", ""),
            "parse_confidence": confidence,
            "parse_notes": "|".join(parse_notes),
            "raw_source_path": str(raw_source_path),
        }
        rows.append(row)
    return rows


def run(input_path: Path, output_path: Path | None = None, snapshot_ts: str | None = None) -> tuple[Path, int]:
    ensure_dirs()
    snapshot_ts = snapshot_ts or utc_now_iso()
    snapshot, raw = load_json_if_possible(input_path)
    snapshot_id = stable_snapshot_id(raw)
    raw_path = store_raw_snapshot(input_path, snapshot_id)
    output_path = output_path or (DATA_PROCESSED / "gmgn_trend_snapshots.csv")

    if snapshot is None:
        write_csv(output_path, [], FIELDNAMES)
        return output_path, 0

    rows = parse_rows(snapshot, snapshot_id, raw_path, snapshot_ts)
    write_csv(output_path, rows, FIELDNAMES)
    return output_path, len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse a stored GMGN Trend snapshot into CSV candidate rows.")
    parser.add_argument("--input", required=True, help="Path to raw GMGN Trend JSON/text/html snapshot")
    parser.add_argument("--output", default="", help="Output CSV path, default data/processed/gmgn_trend_snapshots.csv")
    parser.add_argument("--snapshot-ts", default="", help="ISO timestamp for snapshot; defaults to now UTC")
    args = parser.parse_args()

    output_path = Path(args.output) if args.output else None
    out, count = run(Path(args.input), output_path, args.snapshot_ts or None)
    print(f"Wrote {count} GMGN trend rows to {out}")


if __name__ == "__main__":
    main()

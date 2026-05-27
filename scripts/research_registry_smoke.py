#!/usr/bin/env python3
"""Create one research_run and one research_finding in the live registry.

This is the smallest end-to-end proof that the runtime can write to the current
research_* canon without creating any alternate schema.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from repositories import ResearchRepo  # noqa: E402


DEFAULT_RUN_KEY = "research_registry_smoke_2026_05_27"
DEFAULT_WALLET = "7BNaxx6KdUYrjACNQZ9He26NBFoFxujQMAfNLnArLGH5"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-test live research_* registry writes")
    parser.add_argument("--run-key", default=DEFAULT_RUN_KEY)
    parser.add_argument("--target-wallet", default=DEFAULT_WALLET)
    parser.add_argument("--env-file", default=str(ROOT / ".env"))
    parser.add_argument("--dry-run", action="store_true", help="Print payloads without writing to Supabase")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_dotenv(args.env_file)
    run_payload = {
        "run_key": args.run_key,
        "target_wallet": args.target_wallet,
        "phase": "schema_smoke",
        "verdict": "RESEARCH_REGISTRY_WRITE_TEST",
        "summary": "Smoke proof that runtime writes to research_runs and research_findings on the current canon.",
    }
    finding_payload = {
        "run_key": args.run_key,
        "finding_key": "research_registry_write_smoke",
        "truth_label": "FACT",
        "verdict": "PASS_IF_ROW_VISIBLE_IN_RESEARCH_FINDINGS",
        "confidence": 0.9,
        "evidence": "Created by scripts/research_registry_smoke.py; no hypotheses/events/evidence_log tables used.",
    }
    if args.dry_run:
        print(json.dumps({"run": run_payload, "finding": finding_payload}, indent=2, ensure_ascii=False))
        return 0

    repo = ResearchRepo.from_env()
    run_result = repo.upsert_run(**run_payload)
    finding_result = repo.upsert_finding(**finding_payload)
    print(json.dumps({"run": run_result, "finding": finding_result}, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

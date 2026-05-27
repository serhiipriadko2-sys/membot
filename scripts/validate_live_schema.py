#!/usr/bin/env python3
"""Validate the live Supabase schema used by membot.

This is a read-only guardrail. It verifies the current six-table canon and
explicitly rejects the old hypotheses/events/evidence_log draft as drift.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from supabase import create_client


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "reports" / "live_schema_validation.json"
EXPECTED_COLUMNS = {
    "dataset_runs": {
        "id",
        "created_at",
        "wallet",
        "label",
        "source",
        "status",
        "stats",
        "notes",
    },
    "dataset_artifacts": {
        "id",
        "run_id",
        "created_at",
        "artifact_type",
        "file_name",
        "content_format",
        "row_count",
        "sha256",
        "content_text",
        "content_json",
        "metadata",
    },
    "research_runs": {
        "id",
        "run_key",
        "target_wallet",
        "phase",
        "verdict",
        "summary",
        "created_at",
    },
    "research_artifacts": {
        "id",
        "run_key",
        "artifact_path",
        "artifact_kind",
        "rows_count",
        "bytes_count",
        "sha256",
        "notes",
        "created_at",
    },
    "research_findings": {
        "id",
        "run_key",
        "finding_key",
        "truth_label",
        "verdict",
        "confidence",
        "evidence",
        "created_at",
    },
    "execution_lab_metrics": {
        "id",
        "run_key",
        "metric_group",
        "metric_key",
        "metric_value",
        "unit",
        "notes",
        "created_at",
    },
}
REJECTED_DRIFT_TABLES = {"hypotheses", "events", "evidence_log"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate live membot Supabase schema")
    parser.add_argument("--output", default=str(DEFAULT_REPORT), help="JSON report path")
    parser.add_argument("--env-file", default=str(ROOT / ".env"), help="Optional .env path")
    return parser.parse_args()


def supabase_from_env(env_file: str):
    load_dotenv(env_file)
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY/SUPABASE_KEY")
    return create_client(url, key)


def probe_table(client: Any, table_name: str) -> dict[str, Any]:
    try:
        response = client.table(table_name).select("*", count="exact").limit(1).execute()
        rows = response.data or []
        observed_columns = set(rows[0].keys()) if rows else set()
        expected = EXPECTED_COLUMNS[table_name]
        # Empty tables do not reveal columns through PostgREST. In that case the
        # table existence check still passes, and column-level validation remains
        # unknown rather than false.
        return {
            "table": table_name,
            "exists": True,
            "count": response.count,
            "observed_columns": sorted(observed_columns),
            "missing_columns": sorted(expected - observed_columns) if observed_columns else [],
            "column_status": "PASS" if observed_columns and expected.issubset(observed_columns) else "UNKNOWN_EMPTY_OR_NO_ROWS",
        }
    except Exception as exc:  # noqa: BLE001 - CLI validator should report exact table failure
        return {
            "table": table_name,
            "exists": False,
            "error": str(exc),
            "column_status": "FAIL",
        }


def main() -> int:
    args = parse_args()
    client = supabase_from_env(args.env_file)
    tables = [probe_table(client, table_name) for table_name in EXPECTED_COLUMNS]

    drift_results = []
    for table_name in sorted(REJECTED_DRIFT_TABLES):
        try:
            client.table(table_name).select("*", count="exact").limit(1).execute()
            drift_results.append({"table": table_name, "present": True})
        except Exception:
            drift_results.append({"table": table_name, "present": False})

    missing_tables = [item["table"] for item in tables if not item["exists"]]
    unexpected_drift = [item["table"] for item in drift_results if item["present"]]
    verdict = "PASS" if not missing_tables and not unexpected_drift else "FAIL"
    report = {
        "verdict": verdict,
        "expected_table_count": len(EXPECTED_COLUMNS),
        "missing_tables": missing_tables,
        "rejected_drift_tables_present": unexpected_drift,
        "tables": tables,
        "rejected_drift_tables": drift_results,
        "decision_boundary": "Do not create hypotheses/events/evidence_log in the live canon without ADR/design review.",
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

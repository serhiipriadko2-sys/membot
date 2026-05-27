"""Repository adapter for the live research_* Supabase registry.

This module intentionally targets the existing six-table membot canon. It does
not create or depend on the rejected hypotheses/events/evidence_log draft.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping

from supabase import Client, create_client


DEFAULT_TARGET_WALLET = "7BNaxx6KdUYrjACNQZ9He26NBFoFxujQMAfNLnArLGH5"
VALID_TRUTH_LABELS = {"FACT", "INTERP", "HYP", "RISK"}


@dataclass(frozen=True)
class ResearchRun:
    run_key: str
    target_wallet: str
    phase: str
    verdict: str
    summary: str | None = None


@dataclass(frozen=True)
class ResearchFinding:
    run_key: str
    finding_key: str
    truth_label: str
    verdict: str
    confidence: float | None = None
    evidence: str | None = None


class ResearchRepo:
    """Small service-role adapter for research_runs and research_findings."""

    def __init__(self, client: Client) -> None:
        self.client = client

    @classmethod
    def from_env(cls) -> "ResearchRepo":
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError(
                "Missing SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY/SUPABASE_KEY in environment"
            )
        return cls(create_client(url, key))

    def upsert_run(
        self,
        *,
        run_key: str,
        target_wallet: str = DEFAULT_TARGET_WALLET,
        phase: str,
        verdict: str,
        summary: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "run_key": run_key,
            "target_wallet": target_wallet,
            "phase": phase,
            "verdict": verdict,
            "summary": summary,
        }
        response = (
            self.client.table("research_runs")
            .upsert(payload, on_conflict="run_key")
            .execute()
        )
        return _single_or_payload(response.data)

    def upsert_finding(
        self,
        *,
        run_key: str,
        finding_key: str,
        truth_label: str,
        verdict: str,
        confidence: float | None = None,
        evidence: str | None = None,
    ) -> dict[str, Any]:
        label = truth_label.upper().strip()
        if label not in VALID_TRUTH_LABELS:
            raise ValueError(f"truth_label must be one of {sorted(VALID_TRUTH_LABELS)}")
        if confidence is not None and not 0 <= float(confidence) <= 1:
            raise ValueError("confidence must be between 0 and 1")

        payload = {
            "run_key": run_key,
            "finding_key": finding_key,
            "truth_label": label,
            "verdict": verdict,
            "confidence": confidence,
            "evidence": evidence,
        }
        response = (
            self.client.table("research_findings")
            .upsert(payload, on_conflict="run_key,finding_key")
            .execute()
        )
        return _single_or_payload(response.data)

    def record_observer_gate_verdict(
        self,
        *,
        run_key: str,
        gate_result: Mapping[str, Any],
        target_wallet: str = DEFAULT_TARGET_WALLET,
    ) -> dict[str, Any]:
        verdict = str(gate_result.get("verdict", "UNKNOWN"))
        status = str(gate_result.get("status", verdict))
        row_count = gate_result.get("row_count")
        coverage = gate_result.get("coverage_pct")
        p50 = gate_result.get("p50_total_latency_ms")
        p90 = gate_result.get("p90_total_latency_ms")

        self.upsert_run(
            run_key=run_key,
            target_wallet=target_wallet,
            phase="observer_gate",
            verdict=status,
            summary=(
                f"Observer gate {verdict}: rows={row_count}, coverage={coverage}, "
                f"p50_total_ms={p50}, p90_total_ms={p90}."
            ),
        )

        truth_label = "FACT" if verdict == "PASS" else "RISK"
        confidence = _confidence_from_gate(gate_result)
        evidence = (
            f"row_count={row_count}; coverage_pct={coverage}; "
            f"p50_total_latency_ms={p50}; p90_total_latency_ms={p90}; "
            f"reasons={gate_result.get('reasons', [])}"
        )
        return self.upsert_finding(
            run_key=run_key,
            finding_key="observer_gate_verdict",
            truth_label=truth_label,
            verdict=status,
            confidence=confidence,
            evidence=evidence,
        )


def _single_or_payload(data: Any) -> dict[str, Any]:
    if isinstance(data, list) and data:
        item = data[0]
        return dict(item) if isinstance(item, dict) else {"data": item}
    if isinstance(data, dict):
        return data
    return {"data": data}


def _confidence_from_gate(gate_result: Mapping[str, Any]) -> float:
    row_count = float(gate_result.get("row_count") or 0)
    coverage = float(gate_result.get("coverage_pct") or 0) / 100.0
    live_confirmed = bool(gate_result.get("live_network_confirmed"))
    if not live_confirmed:
        return min(0.45, round(0.2 + min(row_count, 50) / 250.0, 3))
    return round(max(0.5, min(0.98, 0.6 + 0.25 * coverage + min(row_count, 200) / 1000.0)), 3)

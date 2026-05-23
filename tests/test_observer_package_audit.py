from __future__ import annotations

import sys
import zipfile
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

audit = import_module("observer_package_audit")


def write_zip(path: Path, files: dict[str, str]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        for name, text in files.items():
            archive.writestr(name, text)


def test_package_audit_flags_missing_required_files_and_cache_noise(tmp_path: Path) -> None:
    package = tmp_path / "observer.zip"
    write_zip(
        package,
        {
            "reports/observer_status_2026_05_23.md": "ACTIVE / GATE FAILED",
            ".cache/pip/http/foo": "cache",
        },
    )

    result = audit.audit_zip(package)

    assert result["accepted"] is False
    assert "fast10_detector_emitter.py" in result["missing_required"]
    assert any(".cache/pip/http/foo" in entry for entry in result["noise_entries"])


def test_package_audit_accepts_clean_package_and_hashes_artifacts(tmp_path: Path) -> None:
    package = tmp_path / "observer.zip"
    write_zip(
        package,
        {
            "scripts/fast10_detector_emitter.py": "# source",
            "scripts/observer_gate_eval.py": "# source",
            "README_RUNBOOK.md": "# runbook",
            "data/processed/observer_latency_live.csv": "signal_ts_ms,detected_ts_ms,quote_start_ts_ms,quote_end_ts_ms,detector_latency_ms,quote_latency_ms,total_latency_ms,quote_ok,error\n",
            "reports/observer_gate_report.md": "# report",
        },
    )

    result = audit.audit_zip(package)

    assert result["accepted"] is True
    assert result["missing_required"] == []
    assert {artifact["name"] for artifact in result["artifacts"]} >= {
        "scripts/fast10_detector_emitter.py",
        "scripts/observer_gate_eval.py",
        "README_RUNBOOK.md",
    }
    assert all(len(artifact["sha256"]) == 64 for artifact in result["artifacts"])


def test_package_audit_flags_private_key_material(tmp_path: Path) -> None:
    package = tmp_path / "observer.zip"
    write_zip(
        package,
        {
            "scripts/fast10_detector_emitter.py": "# source",
            "scripts/observer_gate_eval.py": "# source",
            "README_RUNBOOK.md": "# runbook",
            "data/processed/observer_latency_live.csv": "signal_ts_ms,detected_ts_ms,quote_start_ts_ms,quote_end_ts_ms,detector_latency_ms,quote_latency_ms,total_latency_ms,quote_ok,error\n",
            "secret.txt": "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----",  # pragma: allow-secret-scan
        },
    )

    result = audit.audit_zip(package)

    assert result["accepted"] is False
    assert result["secret_findings"]
    assert result["secret_findings"][0]["pattern"] == "private_key_block"

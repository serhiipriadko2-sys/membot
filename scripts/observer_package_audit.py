#!/usr/bin/env python3
"""Audit an Observer delivery ZIP before treating it as a runnable package."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "reports" / "observer_package_audit_2026_05_23.md"
DEFAULT_JSON = ROOT / "reports" / "observer_package_audit_2026_05_23.json"

REQUIRED_BASENAMES = [
    "fast10_detector_emitter.py",
    "observer_gate_eval.py",
    "README_RUNBOOK.md",
    "observer_latency_live.csv",
]

NOISE_PARTS = {
    ".cache",
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
}

NOISE_PREFIXES = (
    ".cache/",
    "pip/",
)

SKIP_SECRET_SCAN_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".zip",
    ".gz",
    ".parquet",
    ".sqlite",
    ".db",
}

SECRET_PATTERNS = {
    "private_key_block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |)?PRIVATE KEY-----"),
    "seed_phrase": re.compile(r"(?i)\b(seed phrase|mnemonic)\b\s*[:=]"),
    "supabase_secret_key": re.compile(r"\bsb_" + r"secret_[A-Za-z0-9_-]{20,}\b"),  # pragma: allow-secret-scan
    "openai_api_key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "legacy_jwt_like_key": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    "helius_assignment": re.compile(r"(?i)\bHELIUS_[A-Z0-9_]*KEY\s*[:=]\s*['\"]?([^'\"\s#]+)"),
    "jupiter_assignment": re.compile(r"(?i)\bJUPITER_[A-Z0-9_]*KEY\s*[:=]\s*['\"]?([^'\"\s#]+)"),
    "dune_assignment": re.compile(r"(?i)\bDUNE_[A-Z0-9_]*KEY\s*[:=]\s*['\"]?([^'\"\s#]+)"),
}

PLACEHOLDER_MARKERS = (
    "...",
    "example",
    "placeholder",
    "redacted",
    "dummy",
    "changeme",
    "replace",
    "your_",
    "your-",
    "${",
    "<",
    ">",
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_name(name: str) -> str:
    return name.replace("\\", "/").strip("/")


def is_noise_entry(name: str) -> bool:
    normalized = normalize_name(name)
    parts = normalized.split("/")
    if any(part in NOISE_PARTS for part in parts):
        return True
    return any(normalized.startswith(prefix) for prefix in NOISE_PREFIXES)


def is_placeholder(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def redact(value: str) -> str:
    return "[REDACTED]"


def should_secret_scan(name: str, size: int) -> bool:
    suffix = Path(name).suffix.lower()
    return size <= 2_000_000 and suffix not in SKIP_SECRET_SCAN_SUFFIXES


def scan_text_for_secrets(name: str, text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for pattern_name, pattern in SECRET_PATTERNS.items():
            for match in pattern.finditer(line):
                sample = match.group(1) if match.groups() else match.group(0)
                if is_placeholder(sample):
                    continue
                findings.append(
                    {
                        "path": name,
                        "line": line_no,
                        "pattern": pattern_name,
                        "sample": redact(sample),
                    }
                )
    return findings


def audit_zip(path: Path) -> dict[str, Any]:
    names: list[str] = []
    artifacts: list[dict[str, Any]] = []
    noise_entries: list[str] = []
    secret_findings: list[dict[str, Any]] = []

    with zipfile.ZipFile(path, "r") as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = normalize_name(info.filename)
            names.append(name)
            payload = archive.read(info)
            if is_noise_entry(name):
                noise_entries.append(name)
            else:
                artifacts.append({"name": name, "bytes": len(payload), "sha256": sha256_bytes(payload)})
            if should_secret_scan(name, len(payload)):
                text = payload.decode("utf-8", errors="ignore")
                secret_findings.extend(scan_text_for_secrets(name, text))

    basenames = {Path(name).name for name in names}
    missing_required = [required for required in REQUIRED_BASENAMES if required not in basenames]
    accepted = not missing_required and not noise_entries and not secret_findings
    return {
        "package": str(path),
        "package_bytes": path.stat().st_size,
        "package_sha256": sha256_file(path),
        "accepted": accepted,
        "required_basenames": REQUIRED_BASENAMES,
        "missing_required": missing_required,
        "noise_entries": noise_entries,
        "secret_findings": secret_findings,
        "artifacts": artifacts,
    }


def render_report(result: dict[str, Any]) -> str:
    verdict = "PASS" if result["accepted"] else "FAIL"
    lines = [
        "# Observer Package Audit",
        "",
        f"- Package: `{result['package']}`",
        f"- Verdict: `{verdict}`",
        f"- Bytes: `{result['package_bytes']}`",
        f"- SHA256: `{result['package_sha256']}`",
        "- Safety receipt: `NO_PRIVATE_KEYS` if and only if secret findings are empty.",
        "",
        "## Required Files",
        "",
    ]
    if result["missing_required"]:
        lines.extend(f"- MISSING: `{name}`" for name in result["missing_required"])
    else:
        lines.append("- PASS: all required basenames found.")

    lines.extend(["", "## Noise Entries", ""])
    if result["noise_entries"]:
        lines.extend(f"- `{name}`" for name in result["noise_entries"][:100])
    else:
        lines.append("- PASS: no cache/workspace noise detected.")

    lines.extend(["", "## Secret Findings", ""])
    if result["secret_findings"]:
        for finding in result["secret_findings"]:
            lines.append(
                f"- `{finding['path']}:{finding['line']}` pattern=`{finding['pattern']}` sample=`{finding['sample']}`"
            )
    else:
        lines.append("- PASS: no high-risk secret candidates detected.")

    lines.extend(["", "## Accepted Artifact Hashes", ""])
    if result["artifacts"]:
        lines.extend(
            f"- `{artifact['name']}` bytes=`{artifact['bytes']}` sha256=`{artifact['sha256']}`"
            for artifact in result["artifacts"]
        )
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit Observer delivery ZIP manifest, hashes, noise, and secrets")
    parser.add_argument("zip_path", help="Path to observer delivery ZIP")
    parser.add_argument("--report", default=str(DEFAULT_REPORT), help="Markdown report path")
    parser.add_argument("--json", default=str(DEFAULT_JSON), help="JSON report path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = audit_zip(Path(args.zip_path))
    report = render_report(result)

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")

    json_path = Path(args.json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print(report)
    return 0 if result["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".streamlit",
    "dist",
    "build",
}

SKIP_SUFFIXES = {
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

PLACEHOLDER_MARKERS = (
    "example",
    "placeholder",
    "redacted",
    "dummy",
    "changeme",
    "your_",
    "<",
    ">",
    "${",
    "xxx",
)


@dataclass(frozen=True)
class PatternSpec:
    name: str
    regex: re.Pattern[str]
    severity: str = "FAIL"


PATTERNS = (
    PatternSpec(
        "supabase_secret_key",
        re.compile(r"\bsb_" + r"secret_[A-Za-z0-9_-]{20,}\b"),
    ),
    PatternSpec(
        "openai_api_key",
        re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    ),
    PatternSpec(
        "legacy_jwt_like_key",
        re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    ),
    PatternSpec(
        "private_key_block",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |)?PRIVATE KEY-----"),
    ),
    PatternSpec(
        "service_role_assignment",
        re.compile(r"(?i)(SUPABASE_)?SERVICE_ROLE(_KEY)?\s*[:=]\s*['\"]?([^'\"\s#]+)"),
    ),
    PatternSpec(
        "supabase_secret_assignment",
        re.compile(r"(?i)SUPABASE_(SECRET|SERVICE_ROLE|ADMIN).*?\s*[:=]\s*['\"]?([^'\"\s#]+)"),
    ),
)


@dataclass
class Finding:
    path: Path
    line_no: int
    pattern: str
    severity: str
    sample: str


def should_skip(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if any(part in SKIP_DIRS for part in rel.parts):
        return True
    if path.suffix.lower() in SKIP_SUFFIXES:
        return True
    return False


def is_placeholder(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def redact(value: str) -> str:
    value = value.strip()
    if len(value) <= 10:
        return "[REDACTED]"
    return value[:6] + "...[REDACTED]..." + value[-4:]


def scan_file(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return findings

    for line_no, line in enumerate(text.splitlines(), start=1):
        if "# pragma: allow-secret-scan" in line:
            continue
        for spec in PATTERNS:
            for match in spec.regex.finditer(line):
                sample = match.group(0)
                if spec.name.endswith("assignment") and match.groups():
                    sample = match.group(len(match.groups()))
                if is_placeholder(sample):
                    continue
                findings.append(
                    Finding(
                        path=path.relative_to(ROOT),
                        line_no=line_no,
                        pattern=spec.name,
                        severity=spec.severity,
                        sample=redact(sample),
                    )
                )
    return findings


def iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for current_root, dirs, names in os.walk(root):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRS]
        for name in names:
            path = Path(current_root) / name
            if not should_skip(path):
                files.append(path)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan tracked repository files for high-risk secrets.")
    parser.add_argument("--root", default=str(ROOT), help="Repository root to scan.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    findings: list[Finding] = []
    for path in iter_files(root):
        findings.extend(scan_file(path))

    if not findings:
        print("SECURITY_SCAN_PASS: no high-risk secret candidates found.")
        return 0

    print("SECURITY_SCAN_FAIL: high-risk secret candidates found.")
    for finding in findings:
        print(
            f"{finding.severity}: {finding.path}:{finding.line_no} "
            f"pattern={finding.pattern} sample={finding.sample}"
        )
    print("Rotate any real leaked key before merging. Do not paste secrets into PR comments.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

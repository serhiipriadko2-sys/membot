from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path

import security_scan


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class HistoryFinding:
    commit: str
    path: str
    line_no: int
    pattern: str
    sample: str


def run_git(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def commit_list(limit: int | None = None) -> list[str]:
    args = ["rev-list", "--all"]
    if limit:
        args.extend(["--max-count", str(limit)])
    result = run_git(args)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def should_skip_path(path: str) -> bool:
    p = Path(path)
    if p.suffix.lower() in security_scan.SKIP_SUFFIXES:
        return True
    if any(part in security_scan.SKIP_DIRS for part in p.parts):
        return True
    return False


def files_at_commit(commit: str) -> list[str]:
    result = run_git(["ls-tree", "-r", "--name-only", commit])
    return [line.strip() for line in result.stdout.splitlines() if line.strip() and not should_skip_path(line.strip())]


def file_text_at_commit(commit: str, path: str) -> str:
    result = run_git(["show", f"{commit}:{path}"], check=False)
    if result.returncode != 0:
        return ""
    return result.stdout


def scan_text(commit: str, path: str, text: str) -> list[HistoryFinding]:
    findings: list[HistoryFinding] = []
    if "\x00" in text:
        return findings
    for line_no, line in enumerate(text.splitlines(), start=1):
        if "# pragma: allow-secret-scan" in line:
            continue
        for spec in security_scan.PATTERNS:
            for match in spec.regex.finditer(line):
                sample = match.group(0)
                if spec.name.endswith("assignment") and match.groups():
                    sample = match.group(len(match.groups()))
                if security_scan.is_placeholder(sample):
                    continue
                findings.append(
                    HistoryFinding(
                        commit=commit[:12],
                        path=path,
                        line_no=line_no,
                        pattern=spec.name,
                        sample=security_scan.redact(sample),
                    )
                )
    return findings


def scan_history(limit: int | None = None) -> list[HistoryFinding]:
    findings: list[HistoryFinding] = []
    commits = commit_list(limit)
    for idx, commit in enumerate(commits, start=1):
        print(f"[scan] commit {idx}/{len(commits)} {commit[:12]}")
        for path in files_at_commit(commit):
            findings.extend(scan_text(commit, path, file_text_at_commit(commit, path)))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan git history for high-risk secret candidates.")
    parser.add_argument("--max-commits", type=int, default=None, help="Optional limit for local debugging.")
    args = parser.parse_args()

    if not (ROOT / ".git").exists():
        raise RuntimeError("security_history_scan.py must run in a git checkout with .git history available")

    findings = scan_history(args.max_commits)
    if not findings:
        print("SECURITY_HISTORY_SCAN_PASS: no high-risk secret candidates found in scanned history.")
        return 0

    print("SECURITY_HISTORY_SCAN_FAIL: high-risk secret candidates found in git history.")
    for finding in findings:
        print(
            f"FAIL: commit={finding.commit} {finding.path}:{finding.line_no} "
            f"pattern={finding.pattern} sample={finding.sample}"
        )
    print("Rotate/revoke real leaked keys before any history cleanup. Do not paste secrets into issues, PRs, screenshots, or chat.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

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


@dataclass(frozen=True)
class HistoryObject:
    object_id: str
    path: str


MAX_BLOB_BYTES = 2_000_000
SKIP_TOP_LEVEL_DIRS = {"data", "output"}


def decode_stream(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.decode("utf-8", errors="replace")


def run_git(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return subprocess.CompletedProcess(
        args=result.args,
        returncode=result.returncode,
        stdout=decode_stream(result.stdout),
        stderr=decode_stream(result.stderr),
    )


def commit_list(limit: int | None = None) -> list[str]:
    args = ["rev-list", "--all"]
    if limit:
        args.extend(["--max-count", str(limit)])
    result = run_git(args)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def should_skip_path(path: str) -> bool:
    p = Path(path)
    if p.parts and p.parts[0] in SKIP_TOP_LEVEL_DIRS:
        return True
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


def parse_history_objects(raw: str) -> list[HistoryObject]:
    objects: list[HistoryObject] = []
    seen_objects: set[str] = set()
    for line in raw.splitlines():
        if not line.strip() or " " not in line:
            continue
        object_id, path = line.split(" ", 1)
        path = path.strip()
        if not object_id or not path:
            continue
        if object_id in seen_objects or should_skip_path(path):
            continue
        seen_objects.add(object_id)
        objects.append(HistoryObject(object_id=object_id, path=path))
    return objects


def history_objects(limit: int | None = None) -> list[HistoryObject]:
    if limit:
        objects: list[HistoryObject] = []
        seen_objects: set[str] = set()
        for commit in commit_list(limit):
            result = run_git(["ls-tree", "-r", commit])
            for line in result.stdout.splitlines():
                if "\t" not in line:
                    continue
                meta, path = line.split("\t", 1)
                parts = meta.split()
                if len(parts) < 3:
                    continue
                object_id = parts[2]
                if object_id in seen_objects or should_skip_path(path):
                    continue
                seen_objects.add(object_id)
                objects.append(HistoryObject(object_id=object_id, path=path))
        return objects
    return parse_history_objects(run_git(["rev-list", "--objects", "--all"]).stdout)


def object_text(object_id: str) -> str:
    size_result = run_git(["cat-file", "-s", object_id], check=False)
    if size_result.returncode != 0:
        return ""
    try:
        size = int(size_result.stdout.strip())
    except ValueError:
        return ""
    if size > MAX_BLOB_BYTES:
        return ""
    result = run_git(["cat-file", "-p", object_id], check=False)
    if result.returncode != 0:
        return ""
    return result.stdout


def first_commit_for_object(object_id: str) -> str:
    result = run_git(["log", "--all", f"--find-object={object_id}", "--format=%H", "-n", "1"], check=False)
    if result.returncode != 0:
        return f"object:{object_id[:12]}"
    commit = next((line.strip() for line in result.stdout.splitlines() if line.strip()), "")
    return commit[:12] if commit else f"object:{object_id[:12]}"


def scan_text(commit: str, path: str, text: str | None) -> list[HistoryFinding]:
    findings: list[HistoryFinding] = []
    if text is None:
        return findings
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
    objects = history_objects(limit)
    for idx, obj in enumerate(objects, start=1):
        print(f"[scan] object {idx}/{len(objects)} {obj.object_id[:12]} {obj.path}")
        object_findings = scan_text(obj.object_id[:12], obj.path, object_text(obj.object_id))
        for finding in object_findings:
            findings.append(
                HistoryFinding(
                    commit=first_commit_for_object(obj.object_id),
                    path=finding.path,
                    line_no=finding.line_no,
                    pattern=finding.pattern,
                    sample=finding.sample,
                )
            )
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

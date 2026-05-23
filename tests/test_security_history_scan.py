from __future__ import annotations

import subprocess
import sys
from importlib import import_module
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

history_scan = import_module("security_history_scan")


def test_run_git_decodes_binary_stdout_without_locale_failure(monkeypatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append(kwargs)
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout=b"hello \x98 world", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = history_scan.run_git(["show", "HEAD:file.txt"])

    assert result.stdout == "hello \ufffd world"
    assert calls[0].get("text") is not True


def test_scan_text_ignores_unreadable_blob() -> None:
    assert history_scan.scan_text("commit", "binary.bin", None) == []


def test_parse_history_objects_skips_duplicate_blob_paths() -> None:
    raw = "\n".join(
        [
            "abc123 README.md",
            "abc123 docs/README_COPY.md",
            "def456 data/raw/huge.csv",
            "ghi789 scripts/run.py",
            "",
        ]
    )

    objects = history_scan.parse_history_objects(raw)

    assert objects == [
        history_scan.HistoryObject(object_id="abc123", path="README.md"),
        history_scan.HistoryObject(object_id="ghi789", path="scripts/run.py"),
    ]

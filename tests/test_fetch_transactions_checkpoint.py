from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

fetch_transactions = import_module("02_fetch_transactions")


def test_fetch_transactions_checkpoints_after_new_success() -> None:
    signature_payload = {
        "wallet": "wallet",
        "items": [
            {"signature": "sig1", "slot": 1},
            {"signature": "sig2", "slot": 2},
        ],
    }
    checkpoints: list[tuple[int, int, int]] = []

    def fake_fetch(signature: str) -> dict[str, object]:
        return {"signature": signature}

    def checkpoint(rows_by_signature: dict[str, dict[str, object]], errors: list[dict[str, object]], skipped: int) -> None:
        checkpoints.append((len(rows_by_signature), len(errors), skipped))

    rows_by_signature, errors, skipped = fetch_transactions.fetch_transactions(
        signature_payload,
        existing={},
        fetch_one=fake_fetch,
        checkpoint=checkpoint,
        checkpoint_every=1,
        sleep=lambda: None,
    )

    assert len(rows_by_signature) == 2
    assert errors == []
    assert skipped == 0
    assert checkpoints == [(1, 0, 0), (2, 0, 0)]

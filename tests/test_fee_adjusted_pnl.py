from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SCRIPT = ROOT / "scripts" / "12_fee_adjusted_pnl.py"
spec = importlib.util.spec_from_file_location("fee_adjusted", SCRIPT)
fee_adjusted = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(fee_adjusted)


def test_fee_adjusted_pnl_basic_math():
    rows = [{"token_mint": "A", "entry_usd": "100", "exit_usd": "120", "observed_fee_usd": "3"}]
    out = fee_adjusted.calculate(rows)
    assert out[0]["gross_pnl_usd"] == 20
    assert out[0]["observed_fee_usd"] == 3
    assert out[0]["net_pnl_usd"] == 17


def test_missing_fee_does_not_become_gmgn_fee():
    rows = [{"token_mint": "A", "entry_usd": "100", "exit_usd": "120"}]
    out = fee_adjusted.calculate(rows)
    assert out[0]["observed_fee_usd"] == 0
    assert out[0]["net_pnl_usd"] == 20
    assert out[0]["fee_confidence"] == "low_missing_observed_fee"


def test_negative_pnl_preserved():
    rows = [{"token_mint": "A", "entry_usd": "100", "exit_usd": "80", "observed_fee_usd": "2"}]
    out = fee_adjusted.calculate(rows)
    assert out[0]["gross_pnl_usd"] == -20
    assert out[0]["net_pnl_usd"] == -22

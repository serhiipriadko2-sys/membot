from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SCRIPT = ROOT / "scripts" / "13_copy_stress_model.py"
spec = importlib.util.spec_from_file_location("copy_stress", SCRIPT)
copy_stress = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(copy_stress)


def by_scenario(rows, name):
    return next(r for r in rows if r["scenario"] == name)


def test_gmgn_fee_applies_to_buy_and_sell_notional():
    rows = [{"token_mint": "A", "entry_usd": "100", "exit_usd": "120", "net_pnl_usd": "20"}]
    out = copy_stress.stress_rows(rows, gmgn_fee_pct=0.01, extra_fee_usd_per_trade=0)
    ideal = by_scenario(out, "ideal_0s")
    assert ideal["gmgn_fee_usd"] == 2.2


def test_slippage_worsens_entry_and_exit():
    rows = [{"token_mint": "A", "entry_usd": "100", "exit_usd": "120", "net_pnl_usd": "20"}]
    out = copy_stress.stress_rows(rows, gmgn_fee_pct=0, extra_fee_usd_per_trade=0)
    fast = by_scenario(out, "fast_bot_1s")
    assert fast["copy_cost_usd"] > 100
    assert fast["copy_proceeds_usd"] < 120
    assert fast["copy_net_pnl_usd"] < 20


def test_copy_net_pnl_lte_ideal_when_slippage_and_fees_positive():
    rows = [{"token_mint": "A", "entry_usd": "100", "exit_usd": "120", "net_pnl_usd": "20"}]
    out = copy_stress.stress_rows(rows, gmgn_fee_pct=0.01, extra_fee_usd_per_trade=0.05)
    ideal = by_scenario(out, "ideal_0s")
    late = by_scenario(out, "late_copy_15s")
    assert late["copy_net_pnl_usd"] <= ideal["copy_net_pnl_usd"]
    assert late["stress_model_not_latency_replay"] == "true"

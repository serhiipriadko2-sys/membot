import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("latency_sim", ROOT / "scripts" / "07_latency_sim.py")
latency_sim = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = latency_sim
spec.loader.exec_module(latency_sim)


def test_rejects_post_exit_timestamp_delay():
    trade = {
        "token_mint": "MINT",
        "entry_signature": "buy",
        "exit_signature": "sell",
        "entry_time": "1000",
        "exit_time": "1002",
        "entry_slot": "50",
        "exit_slot": "70",
        "token_amount": "10",
        "exit_sol": "2.0",
        "net_pnl_sol": "1.0",
    }
    [row] = latency_sim.simulate_latency([trade], [])
    assert row["status_3s"] == "invalid_after_exit"
    assert row["invalid_reason_3s"] == "delayed_timestamp_gte_exit_time"


def test_rejects_post_exit_slot_delay():
    trade = {
        "token_mint": "MINT",
        "entry_signature": "buy",
        "exit_signature": "sell",
        "entry_time": "1000",
        "exit_time": "1020",
        "entry_slot": "50",
        "exit_slot": "51",
        "token_amount": "10",
        "exit_sol": "2.0",
        "net_pnl_sol": "1.0",
    }
    [row] = latency_sim.simulate_latency([trade], [])
    assert row["status_1slot"] == "invalid_after_exit"
    assert row["invalid_reason_1slot"] == "delayed_slot_gte_exit_slot"

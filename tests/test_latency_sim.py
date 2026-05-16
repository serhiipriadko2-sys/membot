import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("latency_sim", ROOT / "scripts" / "07_latency_sim.py")
latency_sim = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = latency_sim
spec.loader.exec_module(latency_sim)


def test_slot_delay_uses_slot_progression_not_seconds():
    trade = {
        "token_mint": "MINT",
        "entry_signature": "buy",
        "exit_signature": "sell",
        "entry_time": "1000",
        "exit_time": "1010",
        "entry_slot": "50",
        "exit_slot": "55",
        "token_amount": "10",
        "exit_sol": "2.0",
        "net_pnl_sol": "1.0",
    }
    prices = [
        {"token_mint": "MINT", "timestamp": "1001", "slot": "51", "price_sol": "0.11"},
        {"token_mint": "MINT", "timestamp": "1002", "slot": "53", "price_sol": "0.12"},
    ]
    [row] = latency_sim.simulate_latency([trade], prices)
    assert row["status_1slot"] == "valid"
    assert row["delayed_price_1slot"] == 0.11
    assert row["status_3slots"] == "valid"
    assert row["delayed_price_3slots"] == 0.12


def test_time_delay_uses_timestamp_progression():
    trade = {
        "token_mint": "MINT",
        "entry_signature": "buy",
        "exit_signature": "sell",
        "entry_time": "1000",
        "exit_time": "1040",
        "entry_slot": "50",
        "exit_slot": "90",
        "token_amount": "10",
        "exit_sol": "2.0",
        "net_pnl_sol": "1.0",
    }
    prices = [
        {"token_mint": "MINT", "timestamp": "1003", "slot": "70", "price_sol": "0.10"},
        {"token_mint": "MINT", "timestamp": "1010", "slot": "71", "price_sol": "0.20"},
    ]
    [row] = latency_sim.simulate_latency([trade], prices)
    assert row["status_3s"] == "valid"
    assert row["delayed_price_3s"] == 0.10
    assert row["status_10s"] == "valid"
    assert row["delayed_price_10s"] == 0.20

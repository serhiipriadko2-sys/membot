import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("pairing", ROOT / "scripts" / "04_pair_trades.py")
pairing = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pairing
spec.loader.exec_module(pairing)


def test_fifo_pairing_single_buy_sell():
    swaps = [
        {
            "token_mint": "MINT",
            "side": "BUY",
            "token_amount": "10",
            "sol_amount": "1.0",
            "signature": "buy_sig",
            "block_time": "1000",
            "slot": "10",
        },
        {
            "token_mint": "MINT",
            "side": "SELL",
            "token_amount": "10",
            "sol_amount": "1.5",
            "signature": "sell_sig",
            "block_time": "1100",
            "slot": "20",
        },
    ]
    trades = pairing.pair_fifo(swaps)
    assert len(trades) == 1
    trade = trades[0]
    assert trade["entry_signature"] == "buy_sig"
    assert trade["exit_signature"] == "sell_sig"
    assert trade["hold_seconds"] == 100
    assert abs(trade["net_pnl_sol"] - 0.5) < 1e-12

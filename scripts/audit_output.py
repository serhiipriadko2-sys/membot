#!/usr/bin/env python3
"""Comprehensive audit of pipeline output — limit 1000 run."""

import json
import csv
import random
from pathlib import Path
from collections import Counter, defaultdict

root = Path(__file__).resolve().parents[1]

# =====================================================================
# 1. RAW LAYER
# =====================================================================
sigs = json.loads((root / "data" / "raw" / "signatures_raw.json").read_text(encoding="utf-8"))
txs = json.loads((root / "data" / "raw" / "transactions_raw.json").read_text(encoding="utf-8"))

print("=" * 72)
print("1. RAW DATA")
print("=" * 72)
print(f"  signatures_raw: {sigs['count']} sigs (requested {sigs['limit_requested']})")
print(f"  transactions_raw: {txs['count']} txs, {txs['error_count']} errors")
if txs["errors"]:
    print("  ERRORS:")
    for e in txs["errors"]:
        print(f"    {e['signature'][:30]}... => {e['error'][:60]}")
print()

# =====================================================================
# 2. WALLET_SWAPS.CSV
# =====================================================================
with open(root / "data" / "processed" / "wallet_swaps.csv", encoding="utf-8", newline="") as f:
    swaps = list(csv.DictReader(f))

sides = Counter(r["side"] for r in swaps)
confs = Counter(r["parse_confidence"] for r in swaps)
failed = sum(1 for r in swaps if r.get("is_failed") == "true")

print("=" * 72)
print("2. WALLET_SWAPS.CSV")
print("=" * 72)
print(f"  total rows: {len(swaps)}")
print(f"  side distribution: {dict(sides)}")
print(f"  parse_confidence:  {dict(confs)}")
print(f"  failed txs:        {failed}")
print()

# Unique mints
mints_seen = set(r["token_mint"] for r in swaps if r["token_mint"])
print(f"  unique mints traded: {len(mints_seen)}")

# pump.fun vs non-pump
pump_mints = [m for m in mints_seen if m.endswith("pump")]
print(f"  pump.fun mints:     {len(pump_mints)}")
print(f"  non-pump mints:     {len(mints_seen) - len(pump_mints)}")
print()

# =====================================================================
# 3. TRADES_PAIRED.CSV
# =====================================================================
with open(root / "data" / "processed" / "trades_paired.csv", encoding="utf-8", newline="") as f:
    trades = list(csv.DictReader(f))

print("=" * 72)
print("3. TRADES_PAIRED.CSV")
print("=" * 72)
print(f"  total paired trades: {len(trades)}")

if trades:
    pnls = [float(t.get("pnl_sol") or 0) for t in trades]
    holds = [int(float(t.get("hold_seconds") or 0)) for t in trades]
    entries = [float(t.get("entry_sol") or 0) for t in trades]

    winners = [p for p in pnls if p > 0]
    losers = [p for p in pnls if p < 0]
    breakeven = [p for p in pnls if p == 0]

    print(f"  winners:    {len(winners)}")
    print(f"  losers:     {len(losers)}")
    print(f"  breakeven:  {len(breakeven)}")
    print(f"  win rate:   {len(winners)/len(pnls)*100:.1f}%")
    print()

    total_pnl = sum(pnls)
    gross_win = sum(winners) if winners else 0
    gross_loss = sum(losers) if losers else 0
    profit_factor = abs(gross_win / gross_loss) if gross_loss else float("inf")

    print(f"  gross PnL (SOL):     {total_pnl:+.6f}")
    print(f"  gross winners (SOL): {gross_win:+.6f}")
    print(f"  gross losers (SOL):  {gross_loss:+.6f}")
    print(f"  profit factor:       {profit_factor:.3f}")
    print()

    avg_win = (gross_win / len(winners)) if winners else 0
    avg_loss = (gross_loss / len(losers)) if losers else 0
    print(f"  avg win (SOL):       {avg_win:+.6f}")
    print(f"  avg loss (SOL):      {avg_loss:+.6f}")
    print(f"  avg entry size (SOL): {sum(entries)/len(entries):.4f}")
    print(f"  median entry (SOL):  {sorted(entries)[len(entries)//2]:.4f}")
    print()

    sorted_holds = sorted(holds)
    print(f"  hold time (s) — min: {sorted_holds[0]}, median: {sorted_holds[len(sorted_holds)//2]}, max: {sorted_holds[-1]}")
    print(f"  hold time (min) — min: {sorted_holds[0]/60:.1f}, median: {sorted_holds[len(sorted_holds)//2]/60:.1f}, max: {sorted_holds[-1]/60:.1f}")
    print()

    # PnL concentration
    sorted_pnl = sorted(pnls, reverse=True)
    top1 = sorted_pnl[0]
    top5 = sum(sorted_pnl[:5])
    top10 = sum(sorted_pnl[:10])
    print(f"  PnL concentration:")
    print(f"    top 1 trade:   {top1:+.6f} SOL ({top1/total_pnl*100:.1f}% of total)" if total_pnl else "    top 1 trade: N/A")
    print(f"    top 5 trades:  {top5:+.6f} SOL ({top5/total_pnl*100:.1f}% of total)" if total_pnl else "    top 5 trades: N/A")
    print(f"    top 10 trades: {top10:+.6f} SOL ({top10/total_pnl*100:.1f}% of total)" if total_pnl else "    top 10 trades: N/A")
    print()

    # Bottom 5 (worst trades)
    bottom5 = sorted_pnl[-5:]
    print(f"  Worst 5 trades: {[f'{p:+.4f}' for p in bottom5]}")
    print(f"  Best 5 trades:  {[f'{p:+.4f}' for p in sorted_pnl[:5]]}")
    print()

    # Unique mints in paired trades
    trade_mints = Counter(t["token_mint"] for t in trades)
    print(f"  unique mints in paired: {len(trade_mints)}")
    most_traded = trade_mints.most_common(5)
    print(f"  most traded mints:")
    for mint, cnt in most_traded:
        mint_pnl = sum(float(t["pnl_sol"]) for t in trades if t["token_mint"] == mint)
        print(f"    {mint[:20]}...  trades={cnt}  net_pnl={mint_pnl:+.4f}")
    print()

# =====================================================================
# 4. UNPAIRED AUDIT
# =====================================================================
print("=" * 72)
print("4. UNPAIRED AUDIT")
print("=" * 72)

# Count buy/sell per mint in swaps
buy_counts = defaultdict(float)
sell_counts = defaultdict(float)
buy_sol = defaultdict(float)
sell_sol = defaultdict(float)

for r in swaps:
    mint = r.get("token_mint", "")
    side = r.get("side", "")
    sol = float(r.get("sol_amount") or 0)
    tok = float(r.get("token_amount") or 0)
    if side == "BUY":
        buy_counts[mint] += tok
        buy_sol[mint] += sol
    elif side == "SELL":
        sell_counts[mint] += tok
        sell_sol[mint] += sol

all_mints = set(buy_counts) | set(sell_counts)
fully_paired = 0
unpaired_buy_only = 0
unpaired_sell_only = 0
partial_paired = 0
open_inventory_sol = 0.0

for mint in all_mints:
    b = buy_counts.get(mint, 0)
    s = sell_counts.get(mint, 0)
    if b > 0 and s > 0:
        if abs(b - s) / max(b, s) < 0.01:
            fully_paired += 1
        else:
            partial_paired += 1
            if b > s:
                open_inventory_sol += buy_sol.get(mint, 0) * ((b - s) / b) if b else 0
    elif b > 0 and s == 0:
        unpaired_buy_only += 1
        open_inventory_sol += buy_sol.get(mint, 0)
    elif s > 0 and b == 0:
        unpaired_sell_only += 1

total_buys = sum(1 for r in swaps if r["side"] == "BUY")
total_sells = sum(1 for r in swaps if r["side"] == "SELL")

print(f"  total BUY rows:      {total_buys}")
print(f"  total SELL rows:     {total_sells}")
print(f"  unique mints:        {len(all_mints)}")
print(f"  fully paired mints:  {fully_paired}")
print(f"  partial paired:      {partial_paired}")
print(f"  buy-only (no sell):  {unpaired_buy_only}")
print(f"  sell-only (no buy):  {unpaired_sell_only}")
print(f"  est. open inventory: {open_inventory_sol:.4f} SOL (cost basis)")
print()

# =====================================================================
# 5. FEE ANALYSIS
# =====================================================================
print("=" * 72)
print("5. FEE ANALYSIS")
print("=" * 72)

fees = [int(r.get("fee_lamports") or 0) for r in swaps]
total_fee_sol = sum(fees) / 1_000_000_000
avg_fee = (total_fee_sol / len(fees)) if fees else 0

print(f"  total observed fees:   {total_fee_sol:.6f} SOL")
print(f"  avg fee per swap:      {avg_fee:.6f} SOL")
print(f"  fee range (lamports):  {min(fees)} – {max(fees)}")

if trades:
    print(f"  gross PnL:             {total_pnl:+.6f} SOL")
    print(f"  fees (all swaps):     -{total_fee_sol:.6f} SOL")
    print(f"  fee-adjusted PnL:      {total_pnl - total_fee_sol:+.6f} SOL")
print()

# =====================================================================
# 6. RANDOM SPOT-CHECK (10 signatures)
# =====================================================================
print("=" * 72)
print("6. RANDOM SPOT-CHECK (10 signatures)")
print("=" * 72)

random.seed(42)
sample = random.sample(swaps, min(10, len(swaps)))
for i, r in enumerate(sample):
    print(f"  [{i+1}] sig={r['signature'][:30]}...")
    print(f"       side={r['side']}  mint={r['token_mint'][:20]}...")
    print(f"       token_amt={r['token_amount']}  sol_amt={r['sol_amount']}")
    print(f"       fee={r['fee_lamports']}  conf={r['parse_confidence']}")
    print()

print("=" * 72)
print("AUDIT COMPLETE")
print("=" * 72)

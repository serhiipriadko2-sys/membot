#!/usr/bin/env python3
"""
Deep forensic behavioral analysis of the target wallet.
Combines Helius enriched data with our pipeline CSVs for maximum insight.
"""

import json
import csv
import os
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")
WALLET = os.getenv("TARGET_WALLET", "7BNaxx6KdUYrjACNQZ9He26NBFoFxujQMAfNLnArLGH5")

# =====================================================================
# A. HELIUS ENRICHED TRANSACTION ANALYSIS (last 100 txs)
# =====================================================================
def fetch_enriched(limit=100):
    """Fetch enriched transactions from Helius."""
    all_txs = []
    url = f"https://api.helius.xyz/v0/addresses/{WALLET}/transactions"
    params = {"api-key": HELIUS_API_KEY, "limit": 50}
    
    for page in range(limit // 50):
        r = requests.get(url, params=params, timeout=30)
        batch = r.json()
        if not batch:
            break
        all_txs.extend(batch)
        # Use last signature as cursor for pagination
        params["before"] = batch[-1]["signature"]
    
    return all_txs


def analyze_enriched(txs):
    """Analyze enriched transaction data for behavioral fingerprinting."""
    print("=" * 72)
    print("A. HELIUS ENRICHED TRANSACTION ANALYSIS")
    print("=" * 72)
    
    # 1. Transaction Type Distribution
    types = Counter(t.get("type", "UNKNOWN") for t in txs)
    sources = Counter(t.get("source", "UNKNOWN") for t in txs)
    
    print(f"\n  Total enriched txs analyzed: {len(txs)}")
    print(f"  Transaction types: {dict(types)}")
    print(f"  DEX sources: {dict(sources)}")
    
    # 2. Timing Analysis (Bot Fingerprinting)
    swaps = [t for t in txs if t.get("type") == "SWAP"]
    if swaps:
        timestamps = sorted(s["timestamp"] for s in swaps)
        gaps = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps) - 1)]
        
        print(f"\n  === TIMING ANALYSIS (Bot Fingerprint) ===")
        print(f"  Swap count: {len(swaps)}")
        print(f"  Time span: {timestamps[-1] - timestamps[0]} sec ({(timestamps[-1] - timestamps[0])/3600:.1f} hours)")
        
        if gaps:
            print(f"  Inter-swap gap (sec):")
            print(f"    min={min(gaps)}, median={statistics.median(gaps)}, max={max(gaps)}, mean={statistics.mean(gaps):.1f}")
            print(f"    stdev={statistics.stdev(gaps):.1f}" if len(gaps) > 1 else "")
            print(f"    gaps < 5s:  {sum(1 for g in gaps if g < 5)} ({sum(1 for g in gaps if g < 5)/len(gaps)*100:.0f}%)")
            print(f"    gaps < 10s: {sum(1 for g in gaps if g < 10)} ({sum(1 for g in gaps if g < 10)/len(gaps)*100:.0f}%)")
            print(f"    gaps < 30s: {sum(1 for g in gaps if g < 30)} ({sum(1 for g in gaps if g < 30)/len(gaps)*100:.0f}%)")
            print(f"    gaps < 60s: {sum(1 for g in gaps if g < 60)} ({sum(1 for g in gaps if g < 60)/len(gaps)*100:.0f}%)")
        
        # 3. 24-hour Activity Heatmap
        print(f"\n  === 24H ACTIVITY HEATMAP (UTC) ===")
        hour_counts = Counter()
        for ts in timestamps:
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            hour_counts[dt.hour] += 1
        
        max_count = max(hour_counts.values()) if hour_counts else 1
        for h in range(24):
            count = hour_counts.get(h, 0)
            bar = "█" * int(count / max_count * 30) if max_count else ""
            print(f"    {h:02d}:00  {bar} {count}")
        
        # Detect 24/7 operation
        active_hours = sum(1 for h in range(24) if hour_counts.get(h, 0) > 0)
        print(f"\n  Active hours: {active_hours}/24")
        if active_hours >= 20:
            print(f"  ⚠️  BOT INDICATOR: Active {active_hours}/24 hours — likely automated")
        
        # 4. Swap Direction Analysis
        buy_count = 0
        sell_count = 0
        for s in swaps:
            desc = s.get("description", "").lower()
            if "bought" in desc:
                buy_count += 1
            elif "sold" in desc:
                sell_count += 1
        
        print(f"\n  === DIRECTION ANALYSIS ===")
        print(f"  Buys in batch:  {buy_count}")
        print(f"  Sells in batch: {sell_count}")
        if buy_count > 0 and sell_count > 0:
            ratio = buy_count / sell_count
            print(f"  Buy/Sell ratio: {ratio:.2f}")
    
    # 5. Fee Analysis from enriched data
    fees = [t.get("fee", 0) for t in txs]
    if fees:
        total_fee_sol = sum(fees) / 1_000_000_000
        print(f"\n  === FEE PROFILE ===")
        print(f"  Total fees (SOL): {total_fee_sol:.6f}")
        print(f"  Avg fee (lamports): {statistics.mean(fees):.0f}")
        print(f"  Fee range: {min(fees)} – {max(fees)} lamports")
        
        # Priority fee detection (Jito/MEV indicator)
        high_fee_txs = sum(1 for f in fees if f > 100000)
        print(f"  High-fee txs (>100K lamports): {high_fee_txs}/{len(fees)} ({high_fee_txs/len(fees)*100:.0f}%)")
    
    return swaps


# =====================================================================
# B. PIPELINE CSV DEEP ANALYSIS
# =====================================================================
def analyze_pipeline_data():
    """Deep analysis of our pipeline's wallet_swaps.csv and trades_paired.csv."""
    
    # Load swaps
    swaps_path = ROOT / "data" / "processed" / "wallet_swaps.csv"
    trades_path = ROOT / "data" / "processed" / "trades_paired.csv"
    
    with open(swaps_path, encoding="utf-8", newline="") as f:
        swaps = list(csv.DictReader(f))
    with open(trades_path, encoding="utf-8", newline="") as f:
        trades = list(csv.DictReader(f))
    
    print("\n" + "=" * 72)
    print("B. PIPELINE DEEP BEHAVIORAL ANALYSIS")
    print("=" * 72)
    
    # 1. Entry Size Distribution
    entries = [float(t.get("entry_sol") or 0) for t in trades if float(t.get("entry_sol") or 0) > 0]
    if entries:
        print(f"\n  === ENTRY SIZE PROFILING ===")
        print(f"  Total trades: {len(entries)}")
        print(f"  Mean entry: {statistics.mean(entries):.4f} SOL")
        print(f"  Median entry: {statistics.median(entries):.4f} SOL")
        print(f"  Stdev: {statistics.stdev(entries):.4f} SOL" if len(entries) > 1 else "")
        print(f"  Min: {min(entries):.4f}, Max: {max(entries):.4f}")
        
        # Distribution buckets
        buckets = {"<0.5 SOL": 0, "0.5-1 SOL": 0, "1-2 SOL": 0, "2-5 SOL": 0, "5-10 SOL": 0, ">10 SOL": 0}
        for e in entries:
            if e < 0.5: buckets["<0.5 SOL"] += 1
            elif e < 1: buckets["0.5-1 SOL"] += 1
            elif e < 2: buckets["1-2 SOL"] += 1
            elif e < 5: buckets["2-5 SOL"] += 1
            elif e < 10: buckets["5-10 SOL"] += 1
            else: buckets[">10 SOL"] += 1
        
        print(f"  Size distribution:")
        for k, v in buckets.items():
            pct = v / len(entries) * 100
            bar = "█" * int(pct / 2)
            print(f"    {k:>10s}: {v:>4d} ({pct:5.1f}%) {bar}")
    
    # 2. Hold Time Distribution
    holds = [float(t.get("hold_seconds") or 0) for t in trades if float(t.get("hold_seconds") or 0) > 0]
    if holds:
        print(f"\n  === HOLD TIME PROFILING ===")
        print(f"  Mean: {statistics.mean(holds)/60:.1f} min")
        print(f"  Median: {statistics.median(holds)/60:.1f} min")
        
        hold_buckets = {"<1 min": 0, "1-5 min": 0, "5-15 min": 0, "15-30 min": 0, "30-60 min": 0, "1-2 hr": 0, ">2 hr": 0}
        for h in holds:
            m = h / 60
            if m < 1: hold_buckets["<1 min"] += 1
            elif m < 5: hold_buckets["1-5 min"] += 1
            elif m < 15: hold_buckets["5-15 min"] += 1
            elif m < 30: hold_buckets["15-30 min"] += 1
            elif m < 60: hold_buckets["30-60 min"] += 1
            elif m < 120: hold_buckets["1-2 hr"] += 1
            else: hold_buckets[">2 hr"] += 1
        
        print(f"  Distribution:")
        for k, v in hold_buckets.items():
            pct = v / len(holds) * 100
            bar = "█" * int(pct / 2)
            print(f"    {k:>10s}: {v:>4d} ({pct:5.1f}%) {bar}")
    
    # 3. PnL vs Hold Time Correlation
    if trades:
        print(f"\n  === PnL vs HOLD TIME CORRELATION ===")
        quick_trades = [t for t in trades if float(t.get("hold_seconds") or 0) < 300]  # <5 min
        medium_trades = [t for t in trades if 300 <= float(t.get("hold_seconds") or 0) < 1800]  # 5-30 min
        long_trades = [t for t in trades if float(t.get("hold_seconds") or 0) >= 1800]  # >30 min
        
        for label, group in [("Quick (<5m)", quick_trades), ("Medium (5-30m)", medium_trades), ("Long (>30m)", long_trades)]:
            if group:
                pnls = [float(t.get("pnl_sol") or 0) for t in group]
                wins = sum(1 for p in pnls if p > 0)
                print(f"  {label}: {len(group)} trades, WR={wins/len(group)*100:.0f}%, net PnL={sum(pnls):+.4f} SOL")
    
    # 4. Pump.fun Analysis
    print(f"\n  === PUMP.FUN CONCENTRATION ===")
    pump_swaps = [r for r in swaps if r.get("token_mint", "").endswith("pump")]
    non_pump_swaps = [r for r in swaps if not r.get("token_mint", "").endswith("pump") and r.get("side") in ("BUY", "SELL")]
    print(f"  Pump.fun swaps: {len(pump_swaps)}/{len(swaps)} ({len(pump_swaps)/len(swaps)*100:.0f}%)")
    print(f"  Non-pump swaps: {len(non_pump_swaps)}")
    
    pump_trades = [t for t in trades if t.get("token_mint", "").endswith("pump")]
    non_pump_trades = [t for t in trades if not t.get("token_mint", "").endswith("pump")]
    
    if pump_trades:
        pump_pnl = sum(float(t.get("pnl_sol") or 0) for t in pump_trades)
        pump_wins = sum(1 for t in pump_trades if float(t.get("pnl_sol") or 0) > 0)
        print(f"  Pump.fun paired: {len(pump_trades)}, WR={pump_wins/len(pump_trades)*100:.0f}%, PnL={pump_pnl:+.4f} SOL")
    
    if non_pump_trades:
        np_pnl = sum(float(t.get("pnl_sol") or 0) for t in non_pump_trades)
        np_wins = sum(1 for t in non_pump_trades if float(t.get("pnl_sol") or 0) > 0)
        print(f"  Non-pump paired: {len(non_pump_trades)}, WR={np_wins/len(non_pump_trades)*100:.0f}%, PnL={np_pnl:+.4f} SOL")
    
    # 5. Token Churn Rate
    print(f"\n  === TOKEN CHURN ANALYSIS ===")
    mint_trade_count = Counter(t["token_mint"] for t in trades)
    one_shot = sum(1 for c in mint_trade_count.values() if c == 1)
    repeated = sum(1 for c in mint_trade_count.values() if c > 1)
    heavy = sum(1 for c in mint_trade_count.values() if c >= 5)
    
    print(f"  One-shot tokens (1 trade): {one_shot} ({one_shot/len(mint_trade_count)*100:.0f}%)")
    print(f"  Repeated tokens (2+ trades): {repeated}")
    print(f"  Heavy tokens (5+ trades): {heavy}")
    
    if heavy > 0:
        print(f"  Top heavy-traded tokens:")
        for mint, cnt in mint_trade_count.most_common(5):
            t_pnl = sum(float(t.get("pnl_sol") or 0) for t in trades if t["token_mint"] == mint)
            print(f"    {mint[:20]}... count={cnt} pnl={t_pnl:+.4f}")
    
    # 6. Consecutive Win/Loss Streaks
    if trades:
        print(f"\n  === STREAK ANALYSIS ===")
        pnls = [float(t.get("pnl_sol") or 0) for t in trades]
        
        max_win_streak = 0
        max_loss_streak = 0
        current_streak = 0
        streak_type = None
        
        for p in pnls:
            if p > 0:
                if streak_type == "win":
                    current_streak += 1
                else:
                    current_streak = 1
                    streak_type = "win"
                max_win_streak = max(max_win_streak, current_streak)
            elif p < 0:
                if streak_type == "loss":
                    current_streak += 1
                else:
                    current_streak = 1
                    streak_type = "loss"
                max_loss_streak = max(max_loss_streak, current_streak)
        
        print(f"  Max win streak: {max_win_streak}")
        print(f"  Max loss streak: {max_loss_streak}")
    
    # 7. Risk/Reward Profile
    if trades:
        print(f"\n  === RISK/REWARD PROFILE ===")
        winners = [float(t.get("pnl_sol") or 0) for t in trades if float(t.get("pnl_sol") or 0) > 0]
        losers = [float(t.get("pnl_sol") or 0) for t in trades if float(t.get("pnl_sol") or 0) < 0]
        
        if winners and losers:
            avg_win = statistics.mean(winners)
            avg_loss = abs(statistics.mean(losers))
            rr_ratio = avg_win / avg_loss if avg_loss else float("inf")
            expectancy = (len(winners)/len(pnls) * avg_win) - (len(losers)/len(pnls) * avg_loss)
            
            print(f"  Avg winner: +{avg_win:.4f} SOL")
            print(f"  Avg loser:  -{avg_loss:.4f} SOL")
            print(f"  Risk/Reward ratio: {rr_ratio:.2f}")
            print(f"  Expectancy per trade: {expectancy:+.4f} SOL")
            print(f"  Kelly criterion: {(len(winners)/len(pnls) - (1 - len(winners)/len(pnls))/rr_ratio)*100:.1f}%")


# =====================================================================
# C. BOT CLASSIFICATION SCORING
# =====================================================================
def bot_classification(swaps_data, enriched_swaps):
    """Score the wallet on bot probability indicators."""
    
    print("\n" + "=" * 72)
    print("C. BOT CLASSIFICATION SCORECARD")
    print("=" * 72)
    
    score = 0
    max_score = 0
    indicators = []
    
    # 1. Source concentration (all PUMP_AMM = bot likely)
    sources = Counter(t.get("source", "UNKNOWN") for t in enriched_swaps)
    pump_pct = sources.get("PUMP_AMM", 0) / len(enriched_swaps) * 100 if enriched_swaps else 0
    max_score += 15
    if pump_pct > 90:
        score += 15
        indicators.append(f"  [+15] Source concentration: {pump_pct:.0f}% PUMP_AMM (single-venue focus)")
    elif pump_pct > 70:
        score += 10
        indicators.append(f"  [+10] Source concentration: {pump_pct:.0f}% PUMP_AMM")
    else:
        indicators.append(f"  [ +0] Source diversity detected: {dict(sources)}")
    
    # 2. Transaction velocity
    if enriched_swaps:
        timestamps = sorted(s["timestamp"] for s in enriched_swaps)
        gaps = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps) - 1)]
        if gaps:
            median_gap = statistics.median(gaps)
            fast_pct = sum(1 for g in gaps if g < 30) / len(gaps) * 100
            max_score += 15
            if median_gap < 60:
                score += 15
                indicators.append(f"  [+15] Median gap {median_gap:.0f}s — machine-speed execution")
            elif median_gap < 300:
                score += 8
                indicators.append(f"  [ +8] Median gap {median_gap:.0f}s — fast but human-possible")
            else:
                indicators.append(f"  [ +0] Median gap {median_gap:.0f}s — human-like pacing")
    
    # 3. 24/7 operation
    if enriched_swaps:
        hour_counts = Counter()
        for t in enriched_swaps:
            dt = datetime.fromtimestamp(t["timestamp"], tz=timezone.utc)
            hour_counts[dt.hour] += 1
        active_hours = sum(1 for h in range(24) if hour_counts.get(h, 0) > 0)
        max_score += 10
        if active_hours >= 20:
            score += 10
            indicators.append(f"  [+10] Active {active_hours}/24 hours — no sleep pattern")
        elif active_hours >= 16:
            score += 5
            indicators.append(f"  [ +5] Active {active_hours}/24 hours — extended operation")
        else:
            indicators.append(f"  [ +0] Active {active_hours}/24 hours — human schedule")
    
    # 4. Trade volume (44K+ total from XXYY data)
    max_score += 15
    score += 15
    indicators.append(f"  [+15] 44K+ lifetime txs (XXYY data) — industrial scale")
    
    # 5. Win rate consistency (18 consecutive green days)
    max_score += 15
    score += 15
    indicators.append(f"  [+15] 18 consecutive green days in May 2026 — algorithmic consistency")
    
    # 6. Entry size uniformity
    swaps_path = ROOT / "data" / "processed" / "wallet_swaps.csv"
    with open(swaps_path, encoding="utf-8", newline="") as f:
        csv_swaps = list(csv.DictReader(f))
    
    buy_amounts = [float(r.get("sol_amount") or 0) for r in csv_swaps if r.get("side") == "BUY" and float(r.get("sol_amount") or 0) > 0]
    max_score += 10
    if buy_amounts and len(buy_amounts) > 5:
        cv = statistics.stdev(buy_amounts) / statistics.mean(buy_amounts) if statistics.mean(buy_amounts) > 0 else 0
        if cv < 0.5:
            score += 10
            indicators.append(f"  [+10] Entry size CV={cv:.2f} — highly uniform (programmatic)")
        elif cv < 1.0:
            score += 5
            indicators.append(f"  [ +5] Entry size CV={cv:.2f} — semi-uniform")
        else:
            indicators.append(f"  [ +0] Entry size CV={cv:.2f} — variable (human-like)")
    
    # 7. Fee uniformity
    fees = [int(r.get("fee_lamports") or 0) for r in csv_swaps if int(r.get("fee_lamports") or 0) > 0]
    max_score += 10
    if fees:
        unique_fees = len(set(fees))
        if unique_fees <= 3:
            score += 10
            indicators.append(f"  [+10] Fee uniformity: {unique_fees} unique fee levels — preset configs")
        elif unique_fees <= 10:
            score += 5
            indicators.append(f"  [ +5] Fee variety: {unique_fees} levels")
        else:
            indicators.append(f"  [ +0] Fee diversity: {unique_fees} levels")
    
    # 8. Parse confidence
    high_conf = sum(1 for r in csv_swaps if r.get("parse_confidence") == "high")
    max_score += 10
    if high_conf / len(csv_swaps) > 0.95:
        score += 10
        indicators.append(f"  [+10] {high_conf/len(csv_swaps)*100:.0f}% high-confidence parses — clean execution pattern")
    
    print(f"\n  {'INDICATOR':<60s}")
    print(f"  {'─' * 60}")
    for ind in indicators:
        print(ind)
    
    print(f"\n  {'─' * 60}")
    print(f"  TOTAL SCORE: {score}/{max_score} ({score/max_score*100:.0f}%)")
    print()
    
    if score / max_score > 0.8:
        print(f"  🤖 VERDICT: HIGH PROBABILITY AUTOMATED BOT")
        print(f"     Classification: Pump.fun Scalping / Momentum Bot")
        print(f"     Confidence: {score/max_score*100:.0f}%")
    elif score / max_score > 0.5:
        print(f"  ⚠️  VERDICT: LIKELY SEMI-AUTOMATED")
    else:
        print(f"  👤 VERDICT: LIKELY HUMAN TRADER")


# =====================================================================
# MAIN
# =====================================================================
if __name__ == "__main__":
    print("🔬 FORENSIC DEEP ANALYSIS")
    print(f"   Wallet: {WALLET}")
    print(f"   Time: {datetime.now(timezone.utc).isoformat()}")
    print()
    
    # A. Enriched analysis
    print("Fetching enriched transactions from Helius...")
    enriched = fetch_enriched(limit=100)
    swaps = analyze_enriched(enriched)
    
    # B. Pipeline deep analysis
    analyze_pipeline_data()
    
    # C. Bot classification
    bot_classification(None, swaps)
    
    print("\n" + "=" * 72)
    print("FORENSIC ANALYSIS COMPLETE")
    print("=" * 72)

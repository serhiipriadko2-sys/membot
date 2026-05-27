#!/usr/bin/env python3
"""
Generate synthetic data fixtures for development and testing.

This script creates minimal CSV files in data/processed/ to enable
pipeline testing without requiring live RPC calls or API keys.

WARNING: These are SYNTHETIC fixtures for smoke tests only.
Do NOT use for alpha claims, trading decisions, or research conclusions.
"""

import csv
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

# Base timestamp (recent past)
BASE_TS = datetime(2026, 5, 20, 12, 0, 0)

# Sample token mints (Solana-style base58-ish strings)
SAMPLE_MINTS = [
    "7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr",
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
    "HbxiDXQxBkMN5vVqTxFxnvNhfPsPJFkKZvKUhfQMhDfG",
    "JUPyiJYAv2vEUvvT39kEXQfnN4oGsGEzrHrMXVM9CLhj",
]

# Sample wallet addresses
SAMPLE_WALLET = "7BNaxx6KdUYrACNQZ9He26NBFoFxujQMAfNLnArLGH5"
SAMPLE_COUNTERPARTIES = [
    "4NdSmUfGAbfCi4xmMq7qXZCxJnJKJz8Th1sT2Q9H5abc",
    "5QXdSmUfGAbfCi4xmMq7qXZCxJnJKJz8Th1sT2Q9Hxyz",
    "6RYdSmUfGAbfCi4xmMq7qXZCxJnJKJz8Th1sT2Q9Hlmn",
]


def generate_wallet_swaps(output_path: Path, n_rows: int = 100):
    """Generate synthetic wallet_swaps.csv"""
    rows = []
    for i in range(n_rows):
        ts = BASE_TS + timedelta(seconds=i * 30)
        mint = random.choice(SAMPLE_MINTS)
        is_buy = random.choice([True, False])
        amount_in = round(random.uniform(0.1, 10.0), 6)
        amount_out = round(amount_in * random.uniform(0.95, 1.05), 6)
        price = round(amount_out / amount_in if is_buy else amount_in / amount_out, 8)
        tx_sig = f"{''.join(random.choices('123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz', k=88))}"
        
        rows.append({
            "tx_signature": tx_sig,
            "timestamp": ts.isoformat(),
            "slot": 250000000 + i,
            "wallet_address": SAMPLE_WALLET,
            "mint": mint,
            "side": "buy" if is_buy else "sell",
            "amount_in": amount_in,
            "amount_out": amount_out,
            "price_usd": price,
            "market_cap_usd": round(random.uniform(5000, 85000), 2),
            "liquidity_usd": round(random.uniform(2000, 50000), 2),
            "volume_velocity_tps": round(random.uniform(1, 10), 2),
            "token_age_seconds": random.randint(10, 900),
            "mint_authority_revoked": random.choice([True, True, True, False]),
            "freeze_authority_revoked": random.choice([True, True, True, False]),
            "lp_locked": random.choice([True, True, False]),
            "top10_holders_percent": round(random.uniform(20, 80), 2),
            "pool_address": f"Pool{''.join(random.choices('123456789ABCDEF', k=32))}",
            "jupiter_route": "direct" if random.random() > 0.2 else "multi-hop",
            "priority_fee_lamports": random.randint(1000, 100000),
            "jito_tip_lamports": random.randint(0, 50000),
            "parser_confidence": round(random.uniform(0.85, 1.0), 3),
        })
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Generated {n_rows} rows in {output_path}")


def generate_trades_paired(output_path: Path, n_rows: int = 50):
    """Generate synthetic trades_paired.csv"""
    rows = []
    for i in range(n_rows):
        entry_ts = BASE_TS + timedelta(minutes=i * 10)
        exit_ts = entry_ts + timedelta(minutes=random.randint(5, 120))
        mint = random.choice(SAMPLE_MINTS)
        entry_price = round(random.uniform(0.00001, 0.001), 8)
        pnl_percent = round(random.uniform(-50, 100), 2)
        exit_price = round(entry_price * (1 + pnl_percent / 100), 8)
        
        rows.append({
            "trade_id": f"trade_{i:04d}",
            "wallet_address": SAMPLE_WALLET,
            "mint": mint,
            "entry_timestamp": entry_ts.isoformat(),
            "exit_timestamp": exit_ts.isoformat(),
            "entry_price_usd": entry_price,
            "exit_price_usd": exit_price,
            "entry_market_cap_usd": round(random.uniform(5000, 85000), 2),
            "exit_market_cap_usd": round(exit_price * random.uniform(1e6, 1e8), 2),
            "pnl_percent": pnl_percent,
            "hold_duration_seconds": int((exit_ts - entry_ts).total_seconds()),
            "entry_liquidity_usd": round(random.uniform(2000, 50000), 2),
            "exit_liquidity_usd": round(random.uniform(2000, 50000), 2),
            "entry_token_age_seconds": random.randint(10, 900),
            "exit_token_age_seconds": random.randint(100, 1800),
            "entry_volume_velocity_tps": round(random.uniform(1, 10), 2),
            "exit_volume_velocity_tps": round(random.uniform(1, 10), 2),
            "entry_mint_authority_revoked": True,
            "entry_freeze_authority_revoked": True,
            "entry_lp_locked": random.choice([True, True, False]),
            "entry_top10_holders_percent": round(random.uniform(20, 80), 2),
            "reject_reason": None if pnl_percent > -20 else random.choice(["rapid_dump", "liquidity_collapse", "rug_suspected"]),
        })
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Generated {n_rows} rows in {output_path}")


def generate_entry_context(output_path: Path, n_winners: int = 30, n_losers: int = 30):
    """Generate synthetic entry_context.csv with winners and losers"""
    rows = []
    
    # Winners (positive PnL)
    for i in range(n_winners):
        ts = BASE_TS + timedelta(hours=i)
        mint = SAMPLE_MINTS[i % len(SAMPLE_MINTS)]
        pnl = round(random.uniform(5, 150), 2)
        
        rows.append({
            "anchor_id": f"winner_{i:03d}",
            "wallet_address": SAMPLE_WALLET,
            "mint": mint,
            "entry_timestamp": ts.isoformat(),
            "entry_price_usd": round(random.uniform(0.00001, 0.001), 8),
            "entry_market_cap_usd": round(random.uniform(5000, 85000), 2),
            "entry_liquidity_usd": round(random.uniform(2000, 50000), 2),
            "entry_token_age_seconds": random.randint(10, 900),
            "entry_volume_velocity_tps": round(random.uniform(3, 15), 2),
            "entry_mint_authority_revoked": True,
            "entry_freeze_authority_revoked": True,
            "entry_lp_locked": random.choice([True, True, False]),
            "entry_top10_holders_percent": round(random.uniform(20, 60), 2),
            "outcome_pnl_percent": pnl,
            "outcome_category": "winner",
            "cluster_context_available": random.choice([True, False]),
            "cross_chain_context_available": random.choice([True, False]),
            "market_context_available": random.choice([True, False]),
            "gmgn_trend_snapshot_available": random.choice([True, False]),
        })
    
    # Losers (negative PnL)
    for i in range(n_losers):
        ts = BASE_TS + timedelta(hours=n_winners + i)
        mint = SAMPLE_MINTS[i % len(SAMPLE_MINTS)]
        pnl = round(random.uniform(-80, -5), 2)
        
        rows.append({
            "anchor_id": f"loser_{i:03d}",
            "wallet_address": SAMPLE_WALLET,
            "mint": mint,
            "entry_timestamp": ts.isoformat(),
            "entry_price_usd": round(random.uniform(0.00001, 0.001), 8),
            "entry_market_cap_usd": round(random.uniform(5000, 85000), 2),
            "entry_liquidity_usd": round(random.uniform(2000, 50000), 2),
            "entry_token_age_seconds": random.randint(10, 900),
            "entry_volume_velocity_tps": round(random.uniform(1, 8), 2),
            "entry_mint_authority_revoked": random.choice([True, True, False]),
            "entry_freeze_authority_revoked": random.choice([True, True, False]),
            "entry_lp_locked": random.choice([True, False]),
            "entry_top10_holders_percent": round(random.uniform(40, 90), 2),
            "outcome_pnl_percent": pnl,
            "outcome_category": "loser",
            "cluster_context_available": random.choice([True, False]),
            "cross_chain_context_available": random.choice([True, False]),
            "market_context_available": random.choice([True, False]),
            "gmgn_trend_snapshot_available": random.choice([True, False]),
        })
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Generated {len(rows)} rows ({n_winners} winners, {n_losers} losers) in {output_path}")


def generate_control_points(output_path: Path, n_entries: int = 60):
    """Generate synthetic control_points.csv"""
    rows = []
    offsets = [-300, -120, -60]  # seconds before entry
    
    for i in range(n_entries):
        anchor_type = "winner" if i < n_entries // 2 else "loser"
        anchor_id = f"{anchor_type}_{i % (n_entries // 2):03d}"
        entry_ts = BASE_TS + timedelta(hours=i)
        mint = SAMPLE_MINTS[i % len(SAMPLE_MINTS)]
        
        for offset in offsets:
            ctrl_ts = entry_ts + timedelta(seconds=offset)
            
            rows.append({
                "control_id": f"{anchor_id}_ctrl_{offset}s",
                "anchor_id": anchor_id,
                "wallet_address": SAMPLE_WALLET,
                "mint": mint,
                "control_timestamp": ctrl_ts.isoformat(),
                "offset_seconds": offset,
                "control_market_cap_usd": round(random.uniform(5000, 85000), 2),
                "control_liquidity_usd": round(random.uniform(2000, 50000), 2),
                "control_token_age_seconds": max(10, random.randint(10, 900) + offset),
                "control_volume_velocity_tps": round(random.uniform(1, 10), 2),
                "control_mint_authority_revoked": random.choice([True, True, False]),
                "control_freeze_authority_revoked": random.choice([True, True, False]),
                "control_lp_locked": random.choice([True, False]),
                "control_top10_holders_percent": round(random.uniform(20, 90), 2),
            })
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Generated {len(rows)} rows in {output_path}")


def main():
    """Generate all synthetic datasets"""
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("SYNTHETIC DATA GENERATOR FOR DEVELOPMENT/TESTING")
    print("=" * 60)
    print()
    print("WARNING: These are SYNTHETIC fixtures.")
    print("Do NOT use for alpha claims or trading decisions.")
    print()
    
    generate_wallet_swaps(output_dir / "wallet_swaps.csv", n_rows=100)
    generate_trades_paired(output_dir / "trades_paired.csv", n_rows=50)
    generate_entry_context(output_dir / "entry_context.csv", n_winners=30, n_losers=30)
    generate_control_points(output_dir / "control_points.csv", n_entries=60)
    
    print()
    print("=" * 60)
    print("Synthetic data generation complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  make test-triggers    # Test entry triggers")
    print("  make market-context   # Build market context (requires Dune export)")
    print("  make observer-smoke   # Run Observer smoke test")


if __name__ == "__main__":
    main()

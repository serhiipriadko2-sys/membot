# Membot Architecture

## System Overview

Membot is a forensic research scaffold for reverse-engineering and validating high-frequency Solana meme-trading strategies. The system is organized into distinct layers:

```
┌─────────────────────────────────────────────────────────────┐
│                    Research & Validation                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Hypothesis  │  │   Observer  │  │   Exit Rule Lab     │  │
│  │   Testing   │  │    Gate     │  │   (TP/SL/TS)        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   Context Enrichment Layer                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Cluster   │  │Cross-Chain  │  │   Market-Wide       │  │
│  │   Context   │  │   Context   │  │   (Dune/DEX)        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Entry/Control Pipeline                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Entry     │  │   Control   │  │   Trigger Tests     │  │
│  │   Context   │  │   Points    │  │   (vs Controls)     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Core Data Pipeline                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Fetch     │  │    Pair     │  │   Fee-Adjusted      │  │
│  │ Signatures  │  │   Trades    │  │   PnL               │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Data Sources                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Solana RPC │  │   Helius    │  │   Dune Analytics    │  │
│  │  (Primary)  │  │ (Enhanced)  │  │   (Market-wide)     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
/workspace
├── app/                          # Streamlit UI components
│   ├── streamlit_app.py          # Main dashboard
│   ├── agentic_layer.py          # Agent orchestration
│   └── pages/                    # Dashboard pages
│
├── configs/                      # Configuration files
│   ├── entry_exit_hypotheses.v0.yaml
│   └── prebuy_feature_manifest.yaml
│
├── data/                         # Data artifacts
│   ├── raw/                      # Raw fetched data
│   ├── parsed/                   # Parsed intermediate data
│   └── processed/                # Final analysis-ready CSVs
│
├── docs/                         # Documentation
│   ├── PROTOCOL.md               # Research protocol
│   ├── FAST10_EXECUTION_LAB.md   # Execution lab guide
│   ├── FAST10_OBSERVER.md        # Observer workflow
│   └── HYPOTHESIS_STATUS_MATRIX.md
│
├── queries/                      # SQL queries (Dune)
│   └── dune_m3_solana_trades.sql
│
├── reports/                      # Generated reports
│   ├── observer_gate_report.md
│   └── prebuy_trigger_report.md
│
├── schemas/                      # JSON Schema definitions
│   ├── entry_context.schema.json
│   └── trigger_signal.schema.json
│
├── scripts/                      # Pipeline scripts (00-33+)
│   ├── 00_check_rpc_health.py
│   ├── 01_fetch_signatures.py
│   ├── ...
│   ├── fast10_observer.py
│   └── observer_gate_eval.py
│
├── tests/                        # Test suite
│   ├── test_entry_context.py
│   ├── test_observer_gate_eval.py
│   └── fixtures/
│
└── .github/workflows/            # CI/CD pipelines
    ├── observer_gate_nightly.yml
    └── security-scan.yml
```

## Data Flow

### 1. Signature Fetch (Script 01)
```
Solana RPC → Wallet signatures → data/raw/signatures_*.json
```

### 2. Transaction Fetch (Script 02)
```
Signatures + RPC → Full transactions → data/raw/transactions_*.json
```

### 3. Swap Normalization (Script 03)
```
Transactions → Parser → wallet_swaps.csv
```

### 4. Trade Pairing (Script 04)
```
wallet_swaps.csv → FIFO pairing → trades_paired.csv
```

### 5. Fee-Adjusted PnL (Script 12)
```
trades_paired.csv + fee scans → fee_adjusted_pnl.csv
```

### 6. Entry Context Build (Script 18)
```
trades_paired.csv → Sample winners/losers → entry_context.csv
```

### 7. Control Points (Script 19)
```
entry_context.csv → Same-token offsets → control_points.csv
```

### 8. Trigger Tests (Script 20/29)
```
entry_context.csv + control_points.csv → trigger_tests.csv + report.md
```

### 9. Observer Latency (fast10_observer.py)
```
Signal feed → Detection → Jupiter quote → observer_latency_live.csv
```

### 10. Gate Evaluation (observer_gate_eval.py)
```
observer_latency_live.csv → Metrics → gate report (PASS/FAIL)
```

## Key Components

### Fast10 Detector
Identifies extreme 10-second volume acceleration before entry. Signal formula:
```
Fast10 = volume_10s / volume_300s > p90_threshold
```

### Observer Harness
No-key monitoring tool that measures:
- Signal detection latency
- Jupiter quote latency
- Total signal-to-quote time

Mandatory fields in output CSV:
- `signal_ts_ms`, `detected_ts_ms`
- `quote_start_ts_ms`, `quote_end_ts_ms`
- `detector_latency_ms`, `quote_latency_ms`, `total_latency_ms`
- `quote_ok`, `error`

### Entry vs Control Testing
Compares feature distributions between:
- **Entries**: Actual wallet entry points (30 winners + 30 losers)
- **Controls**: Same-token, pre-entry timestamps (-300s, -120s, -60s)

Statistical tests:
- Kolmogorov-Smirnov for distribution differences
- Mann-Whitney U for median differences
- Effect size (Cohen's d)

### Exit Rule Lab
Sweeps exit parameters on historical entries:
- Take Profit (TP): +5% to +50%
- Stop Loss (SL): -5% to -50%
- Time Stop (TS): 300s to 1800s
- Trailing Stop: optional

Output: PnL distribution, win rate, median return per configuration.

## Safety Boundaries

### NO_PRIVATE_KEYS
No script in this repository:
- Stores private keys
- Signs transactions
- Sends swaps to chain
- Executes trades

### Synthetic Data Policy
Synthetic fixtures (`_generate_synthetic_data.py`) are for:
- ✅ Smoke tests
- ✅ UI development
- ✅ Pipeline integration tests

NOT for:
- ❌ Alpha claims
- ❌ Trading decisions
- ❌ Research conclusions

### Observer Gate Contract
Paper mode requires:
1. Gate status: PASS
2. Minimum live rows: 50
3. Coverage: >90%
4. Median latency: <500ms

Live execution requires additional:
- Security review
- Private-key boundary audit
- Slippage replay validation
- Explicit approval

## Configuration

### Environment Variables (.env)
```bash
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
HELIUS_API_KEY=your_helius_key
DUNE_API_KEY=your_dune_key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_key
```

### Hypothesis Config (configs/entry_exit_hypotheses.v0.yaml)
Defines thresholds and status for all entry/exit hypotheses.

### Feature Manifest (configs/prebuy_feature_manifest.yaml)
Maps features to columns, statistical tests, and expected directions.

## Testing Strategy

### Unit Tests
- Parser logic
- Pairing algorithm
- Latency calculations
- Schema validation

### Integration Tests
- End-to-end pipeline runs
- Cross-script data compatibility
- Report generation

### Contradiction Tests
- Impossible delayed entry after exit
- Partial fill handling
- WSOL wrap/unwrap ambiguity
- Multi-hop route edge cases

## Monitoring & Observability

### Nightly Observer Gate
GitHub Actions workflow runs daily at 2 AM UTC:
- Validates Observer harness
- Generates latency report
- Posts to job summary

### Security Scans
- `security_scan.py`: Current state audit
- `security_history_scan.py`: Historical pattern analysis
- `observer_package_audit.py`: Delivery manifest verification

### Data Quality Checks
- Parser confidence scores
- Nil-value percentages
- Timestamp anomaly detection
- Duplicate transaction flags

## References

- `README.md` — Project overview and current status
- `docs/PROTOCOL.md` — Research methodology
- `docs/FAST10_EXECUTION_LAB.md` — Execution lab protocol
- `docs/FAST10_OBSERVER.md` — Observer workflow
- `CONTRIBUTING.md` — Contribution guidelines
- `scripts/README.md` — Pipeline script documentation

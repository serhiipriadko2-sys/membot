# Troubleshooting Guide

## Common Issues and Solutions

### RPC Connection Failures

**Symptom:** Scripts 01/02 fail with connection timeout or rate limit errors.

**Solutions:**
1. Check RPC health: `make health`
2. Verify `.env` configuration:
   ```bash
   cat .env | grep SOLANA_RPC_URL
   ```
3. Try alternative RPC endpoints (see `docs/RPC_PROVIDER_STRATEGY.md`)
4. Add retry logic with exponential backoff
5. Consider upgrading to paid RPC tier

---

### Missing Data Files

**Symptom:** Downstream scripts fail with "file not found" errors.

**Solutions:**
1. Check which files are missing: `make data-check`
2. Generate synthetic fixtures for development: `make restore-data`
3. Run full pipeline from start:
   ```bash
   python scripts/00_check_rpc_health.py
   python scripts/01_fetch_signatures.py
   python scripts/02_fetch_transactions.py
   python scripts/03_normalize_swaps.py
   python scripts/04_pair_trades.py
   ```

---

### Parser Confidence Low

**Symptom:** `parser_confidence` < 0.8 in wallet_swaps.csv

**Causes:**
- Multi-hop route ambiguity
- Partial fills
- WSOL wrap/unwrap operations
- Unknown instruction types

**Solutions:**
1. Manually audit low-confidence rows
2. Add new parser rules for edge cases
3. Flag ambiguous rows for exclusion from analysis
4. Use Helius enhanced API for better parsing

---

### Trade Pairing Failures

**Symptom:** Unmatched sells, incorrect FIFO pairing

**Solutions:**
1. Check for partial fills in raw transactions
2. Verify timestamp ordering
3. Review WSOL handling logic
4. Run contradiction test: `pytest tests/test_pairing_fifo.py -v`
5. Manually inspect problematic token mints

---

### Observer Gate Fails

**Symptom:** `observer_gate_eval.py` returns FAIL or SMOKE_ONLY

**Solutions:**
1. **SMOKE_ONLY verdict:** This is expected for CSV-only runs. Run with network access for live validation.
2. **FAIL verdict:**
   - Check input file exists and has rows
   - Verify all required fields present
   - Ensure numeric fields parse correctly
   - Run smoke test: `make observer-smoke`

**Required CSV fields:**
```
signal_ts_ms, detected_ts_ms, quote_start_ts_ms, quote_end_ts_ms,
detector_latency_ms, quote_latency_ms, total_latency_ms, quote_ok, error
```

---

### Trigger Tests Show No Separation

**Symptom:** Entry vs control features show no statistical difference

**Possible causes:**
1. Insufficient sample size (< 30 winners/losers)
2. Features not actually predictive
3. Data leakage (market context contaminating controls)
4. Incorrect control point offsets

**Solutions:**
1. Increase sample size
2. Review feature definitions in `configs/prebuy_feature_manifest.yaml`
3. Check for UNKNOWN values in market context columns
4. Verify control timestamps are truly pre-entry

---

### Streamlit App Won't Start

**Symptom:** `streamlit run app/streamlit_app.py` fails

**Solutions:**
1. Install dependencies: `pip install -r requirements.txt`
2. Check for `.streamlit/secrets.toml` if using Supabase
3. Verify data files exist in `data/processed/`
4. Clear cache: `rm -rf .streamlit/cache/`
5. Run with verbose logging:
   ```bash
   streamlit run app/streamlit_app.py --server.headless true --logger.level debug
   ```

---

### Test Failures

**Symptom:** `make test` shows failures

**Solutions:**
1. Run specific test: `pytest tests/test_<name>.py -v`
2. Check test fixtures exist: `ls tests/fixtures/`
3. Verify synthetic data generated: `make restore-data`
4. Look for recent code changes affecting tested functionality
5. Check Python version compatibility (requires 3.11+)

---

### Memory Errors on Large Datasets

**Symptom:** Python process killed (OOM) on large CSV files

**Solutions:**
1. Use chunked processing:
   ```python
   for chunk in pd.read_csv('large_file.csv', chunksize=10000):
       process(chunk)
   ```
2. Filter early in pipeline
3. Use Parquet format for intermediate storage
4. Increase system memory or use cloud instance

---

### Git Issues

**Symptom:** Can't commit/push due to large data files

**Solutions:**
1. Verify `.gitignore` includes `data/` directory
2. Remove accidentally committed data:
   ```bash
   git rm -r --cached data/
   git commit -m "Remove data directory from tracking"
   ```
3. Use Git LFS for large tracked files (if needed)

---

### Environment Variable Issues

**Symptom:** Scripts fail with "missing API key" errors

**Solutions:**
1. Copy example env file: `cp .env.example .env`
2. Edit `.env` with actual values
3. Verify loading in Python:
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   import os
   print(os.getenv('SOLANA_RPC_URL'))
   ```
4. For GitHub Actions, add secrets in repository settings

---

### Performance Issues

**Symptom:** Scripts run very slowly

**Solutions:**
1. Profile slow sections:
   ```bash
   python -m cProfile -o profile.stats script.py
   snakeviz profile.stats
   ```
2. Add caching for repeated API calls
3. Use parallel processing for independent operations
4. Optimize database queries (if using Supabase)
5. Consider vectorization with pandas/numpy

---

### Schema Validation Errors

**Symptom:** JSON schema validation fails

**Solutions:**
1. Check schema version matches data version
2. Validate manually:
   ```python
   import json
   from jsonschema import validate
   with open('data.json') as f:
       data = json.load(f)
   with open('schema.json') as f:
       schema = json.load(f)
   validate(data, schema)
   ```
3. Update schema if adding new fields
4. Check for type mismatches (string vs number)

---

## Getting Help

1. **Check documentation:** `docs/` directory
2. **Review existing issues:** GitHub Issues tab
3. **Run diagnostics:**
   ```bash
   make health
   make data-check
   make test
   ```
4. **Generate debug report:**
   ```bash
   python scripts/audit_output.py
   ```
5. **Create issue** with:
   - Steps to reproduce
   - Expected vs actual behavior
   - Relevant log output
   - Environment details (OS, Python version)

---

## Emergency Contacts

- **RPC provider status:** [Solana Status](https://status.solana.com/)
- **Helius status:** [Helius Discord](https://discord.gg/helius)
- **Dune status:** [Dune Status](https://dune.com/status)
- **GitHub Actions:** [GitHub Status](https://www.githubstatus.com/)

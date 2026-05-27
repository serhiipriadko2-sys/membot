# membot

Research scaffold for reverse-engineering and validating a high-frequency Solana meme-trading wallet.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Tests](https://github.com/membot/membot/actions/workflows/observer_gate_nightly.yml/badge.svg)](https://github.com/membot/membot/actions)

## Current status — 2026-05-27

```text
RESEARCH: PASS
MARKET_FLOW_TRIGGER: PASS
FULL_TAPE_COVERAGE: PASS
EXIT_RULE_LAB: PASS
LATENCY_WARNING: PASS
DATA_PIPELINE: RESTORED ✅
HYPOTHESIS_MATRIX: DOCUMENTED ✅
OBSERVER_GATE: AUTOMATED ✅
TEST_COVERAGE: EXPANDED ✅
LIVE_ALPHA: NOT VERIFIED
TRADING_BOT: FORBIDDEN UNTIL OBSERVER/PAPER PASS
```

This repository is not a trading bot. It is a forensic and execution-lab workspace.

## Quick Start

```bash
# Install dependencies
make install

# Configure environment variables
cp .env.example .env
# Edit .env and add your SUPABASE_KEY (replace YOUR_NEW_SECRET_KEY_HERE)

# Generate synthetic data for development
make restore-data

# Run all tests
make test

# Check data quality
make quality

# Run full CI pipeline locally
make all
```

## Current target

Wallet:
```text
7BNaxx6KdUYrjACNQZ9He26NBFoFxujQMAfNLnArLGH5
```

## Current strongest conclusion

The strongest current candidate is `crescendo_fast_10_p90`, also called **Fast10**.

It identifies extreme 10-second volume acceleration before entry. Full market-tape testing shows the signal is a plausible micro-alpha candidate only if execution is very fast and the exit rule is strict.

Correct wording:
```text
MICRO-ALPHA CANDIDATE DETECTED IN LAB; LIVE ALPHA NOT VERIFIED.
```

Do not use:
```text
ALPHA DECODED
MISSION COMPLETE
READY TO TRADE
```

## Key evidence

| Layer | Current result |
|---|---:|
| Fast10 Signal Detection | ✅ PASS |
| Market Coverage | ✅ 97.45% |
| Walk-forward (100/100 bps) | ⚠️ PARTIAL |
| Best Exit Rule | ⚠️ TP +5%, SL -20%, TS 300s |
| Latency Cliff | ⚠️ ~0.5s |
| Live Alpha | 🔍 NOT VERIFIED |

**Conclusion:** MICRO-ALPHA CANDIDATE DETECTED IN LAB; LIVE ALPHA NOT VERIFIED

## Project Structure

```
membot/
├── scripts/           # Data pipelines and analysis scripts
├── tests/             # Test suite
├── data/              # Raw, parsed, and processed data
├── docs/              # Documentation and protocols
├── configs/           # Configuration files
├── schemas/           # JSON schemas for data validation
├── reports/           # Generated reports
└── .github/           # CI/CD workflows and templates
```

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make help` | Show all available commands |
| `make install` | Install dependencies |
| `make restore-data` | Generate synthetic data fixtures |
| `make test` | Run all tests |
| `make quality` | Run data quality checks |
| `make lint` | Run linters |
| `make format` | Format code with black |
| `make observer-smoke` | Run Observer smoke test |
| `make audit` | Run security audits |
| `make all` | Run full CI pipeline |

## Hypothesis Status

See [docs/HYPOTHESIS_STATUS_MATRIX.md](docs/HYPOTHESIS_STATUS_MATRIX.md) for detailed tracking of all entry and exit hypotheses.

### Entry Hypotheses (H1-H8)
- H1: Market cap sweet spot ($5K-$85K) — 🔍 UNTESTED
- H2: Minimum liquidity ($2K+) — 🔍 UNTESTED  
- H3: Token age window (10s-900s) — 🔍 UNTESTED
- H4: Volume velocity threshold (3+ TPS) — 🔍 UNTESTED
- H5-H7: Anti-rug filters — 📊 RAW_REQUIRED
- H8: Holder concentration (<70%) — 🔍 UNTESTED

### Exit Hypotheses (E1-E6)
- E1: Take profit (5%-50%) — ⚠️ PARTIAL
- E2: Stop loss (-20% to -5%) — ⚠️ PARTIAL
- E3: Time stop (300s-1800s) — ⚠️ PARTIAL
- E4-E6: Advanced exits — 🔍 UNTESTED

## Development

### Pre-commit Hooks

Install pre-commit hooks for automatic formatting and linting:

```bash
pip install pre-commit
pre-commit install
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage
make test-coverage

# Specific test file
pytest tests/test_data_quality.py -v
```

### Data Quality

Run comprehensive data quality checks:

```bash
make quality
```

Checks include:
- Nil/NaN percentage analysis
- Timestamp anomaly detection
- Duplicate transaction detection
- Statistical outlier detection

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — System architecture overview
- [Contributing](CONTRIBUTING.md) — How to contribute
- [Troubleshooting](docs/TROUBLESHOOTING.md) — Common issues and solutions
- [Changelog](CHANGELOG.md) — Version history
- [Hypothesis Matrix](docs/HYPOTHESIS_STATUS_MATRIX.md) — Research hypothesis tracking

## CI/CD

Automated workflows:
- **Observer Gate Nightly** — Daily latency and signal validation
- **Security Scan** — Automated security checks
- **Agent CI Smoke** — Smoke tests for agent components
- **Forensic Verification** — Deep analysis verification

## License

MIT License — see [LICENSE](LICENSE) for details.

## Disclaimer

This is a research project only. Not financial advice. Do not use for live trading without extensive validation and risk management.

# Contributing to Membot

This document provides guidelines for contributing to the membot research project.

## Quick Start

1. **Fork and clone** the repository
2. **Set up environment**: `make install`
3. **Run tests**: `make test`
4. **Generate synthetic data** (for development): `make restore-data`

## Development Workflow

### 1. Branch Naming

- `feature/<description>` — New features or hypotheses
- `fix/<description>` — Bug fixes
- `docs/<description>` — Documentation updates
- `test/<description>` — Test additions
- `refactor/<description>` — Code refactoring

### 2. Pre-commit Checklist

Before committing, ensure:

```bash
make lint      # Run linters
make format    # Format code
make test      # Run tests
```

### 3. Commit Messages

Follow conventional commits format:

```
feat: add Fast10 volume acceleration detector
fix: correct latency calculation in observer
docs: update hypothesis status matrix
test: add boundary case tests for pairing logic
```

### 4. Pull Request Process

1. Create a PR with clear description
2. Link related issues
3. Ensure CI passes
4. Request review from maintainers
5. Address feedback before merge

## Code Standards

### Python Style

- Follow PEP 8
- Use type hints where possible
- Maximum line length: 120 characters
- Docstrings for public functions/classes

### Data Pipeline Scripts

Scripts in `scripts/` should:

1. Accept CLI arguments via `argparse`
2. Write reproducible artifacts (CSV/JSON)
3. Never fabricate data
4. Fail loudly on missing dependencies
5. Log progress to console

Example structure:

```python
#!/usr/bin/env python3
"""Script description."""

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def parse_args():
    parser = argparse.ArgumentParser(description="...")
    parser.add_argument("--input", default=...)
    return parser.parse_args()

def main():
    args = parse_args()
    # Implementation
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

### Tests

Tests should:

- Be independent and isolated
- Use fixtures from `tests/fixtures/`
- Cover edge cases and error conditions
- Run quickly (< 5 seconds per test)

## Research Protocol

### Hypothesis Testing

1. Document hypothesis in `configs/entry_exit_hypotheses.v0.yaml`
2. Update `docs/HYPOTHESIS_STATUS_MATRIX.md`
3. Implement test script
4. Generate report with PASS/FAIL/UNKNOWN markers
5. Never use synthetic data for alpha claims

### Data Integrity

- Source of truth: raw on-chain data
- Parser confidence flags required
- No dashboard screenshots as final proof
- Reproducible artifact generation mandatory

### Observer Gate

Before any live testing:

1. Smoke test passes: `make observer-smoke`
2. Nightly gate validates harness
3. Security review completed
4. NO_PRIVATE_KEYS enforced

## Reporting Issues

Use GitHub Issues with templates:

- **Bug Report**: Steps to reproduce, expected vs actual behavior
- **Hypothesis Proposal**: Feature definition, thresholds, expected outcome
- **Data Quality Issue**: Affected scripts, sample data, confidence impact
- **Documentation Gap**: Missing or unclear documentation

## Release Process

Releases are tagged when:

1. Major hypothesis validated
2. New pipeline stage completed
3. Significant documentation milestone reached

Tag format: `vYYYY.MM.DD-description`

Example: `v2026.05.27-fast10-observer-gate`

## Questions?

- Check existing documentation in `docs/`
- Review closed issues for similar questions
- Open a new issue for clarification

---

**Remember:** This is a research scaffold, not a trading bot. Safety and reproducibility come first.

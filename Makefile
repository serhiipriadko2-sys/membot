# Membot Development Makefile
# Quick reference: make help

.PHONY: help clean install lint format test test-coverage data-check restore-data docs observer-smoke observer-live research-schema-check research-registry-smoke audit

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

clean: ## Remove build artifacts and cache
	rm -rf __pycache__ .pytest_cache .mypy_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf output/ data/processed/*.csv reports/*.json reports/*.md 2>/dev/null || true

install: ## Install dependencies from requirements.txt
	pip install -r requirements.txt
	pip install black flake8 mypy pytest-cov pre-commit

lint: ## Run linters (flake8, mypy)
	flake8 scripts/ app/ tests/ --max-line-length=120 --ignore=E501,W503
	mypy scripts/ app/ tests/ --ignore-missing-imports --no-strict-optional

format: ## Format code with black
	black scripts/ app/ tests/ src/ --line-length=120

test: ## Run all tests
	pytest tests/ -v

test-coverage: ## Run tests with coverage report
	pytest tests/ -v --cov=scripts --cov=app --cov=src --cov-report=html --cov-report=term-missing

data-check: ## Check if processed data files exist
	@echo "Checking for required data files..."
	@if [ ! -f data/processed/wallet_swaps.csv ]; then echo "MISSING: data/processed/wallet_swaps.csv"; fi
	@if [ ! -f data/processed/trades_paired.csv ]; then echo "MISSING: data/processed/trades_paired.csv"; fi
	@if [ ! -f data/processed/entry_context.csv ]; then echo "MISSING: data/processed/entry_context.csv"; fi
	@if [ ! -f data/processed/control_points.csv ]; then echo "MISSING: data/processed/control_points.csv"; fi
	@echo "Data check complete."

restore-data: ## Generate minimal synthetic data fixtures for development/testing
	@echo "Generating synthetic data fixtures..."
	python scripts/_generate_synthetic_data.py
	@echo "Synthetic data generated in data/processed/"

docs: ## Generate documentation stubs
	@echo "Documentation structure already exists in docs/"
	ls -la docs/

observer-smoke: ## Run Observer smoke test (CSV-only, no network)
	python scripts/fast10_detector_emitter.py --output data/processed/observer_latency_live.csv --rows 1
	python scripts/observer_gate_eval.py --input data/processed/observer_latency_live.csv --run-mode smoke

observer-live: ## Run Observer live test (requires network and API keys)
	@echo "WARNING: This requires valid RPC/API configuration"
	python scripts/fast10_observer.py --input data/processed/fast10_live_candidates.csv --output data/processed/observer_latency_live.csv --limit 100
	python scripts/observer_gate_eval.py --input data/processed/observer_latency_live.csv --run-mode live --min-live-rows 50

research-schema-check: ## Validate live Supabase six-table research schema
	python scripts/validate_live_schema.py

research-registry-smoke: ## Write one research_run and one research_finding smoke row
	python scripts/research_registry_smoke.py

audit: ## Run package audit and generate reports
	python scripts/observer_package_audit.py
	python scripts/security_scan.py
	python scripts/security_history_scan.py

health: ## Check RPC health
	python scripts/00_check_rpc_health.py

backtest: ## Run backtest report
	python scripts/14_backtest_report.py

entry-context: ## Build entry context dataset
	python scripts/18_build_entry_context.py --sample-winners 30 --sample-losers 30

control-points: ## Build control points dataset
	python scripts/19_build_control_points.py

test-triggers: ## Test entry triggers
	python scripts/20_test_entry_triggers.py

market-context: ## Build market-wide context
	python scripts/25_build_market_context.py --include-controls

test-market: ## Test market triggers
	python scripts/29_test_market_triggers.py

ci-smoke: ## Run CI smoke test
	python scripts/agent_ci_smoke.py

quality: ## Run data quality checks
	python scripts/data_quality_check.py

all: lint test observer-smoke audit ## Run full local CI pipeline

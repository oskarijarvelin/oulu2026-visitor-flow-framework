PYTHON ?= python3.12
VENV := .venv
BIN := $(VENV)/bin

.PHONY: help venv install install-prophet ingest ingest-full climatology verify \
        forecast forecast-baseline backtest report test lint typecheck check clean \
        web-install web-data web web-dev web-preview web-check web-test web-e2e all

help:
	@echo "make install      Create .venv and install the ingest + forecast + dev groups"
	@echo "make install-prophet  Add the optional prophet group (slow: builds cmdstan)"
	@echo "make ingest       Incremental run (--days-back 7)"
	@echo "make ingest-full  Full rebuild from 2026-01-01"
	@echo "make climatology  Fetch 10-year weather normals (run once)"
	@echo "make verify       Run the quality gates against data/processed without fetching"
	@echo "make forecast     Run both models and write data/forecasts"
	@echo "make forecast-baseline  Run only the baseline model"
	@echo "make backtest     Validate the models without writing forecasts"
	@echo "make report       Print the metrics of the last forecast run"
	@echo "make test         pytest"
	@echo "make lint         ruff check"
	@echo "make typecheck    mypy"
	@echo "make check        lint + typecheck + test"
	@echo ""
	@echo "make web-install  npm install for the web workspace"
	@echo "make web-data     Package data/ into packages/web/src/data/*.json"
	@echo "make web          Build the static site into packages/web/dist"
	@echo "make web-dev      Start the Astro dev server"
	@echo "make web-preview  Serve the built site locally"
	@echo "make web-check    astro check (TypeScript)"
	@echo "make web-test     vitest: transforms and schema validation"
	@echo "make web-e2e      Playwright smoke test against the built site"
	@echo "make all          ingest, forecast, then the web build"

$(BIN)/python:
	$(PYTHON) -m venv $(VENV)

venv: $(BIN)/python

install: venv
	$(BIN)/python -m pip install --upgrade pip
	$(BIN)/python -m pip install -e ".[ingest,forecast,dev]"

# Kept separate because Prophet builds cmdstan, which takes minutes. On macOS the
# XGBoost wheel also needs an OpenMP runtime: brew install libomp.
install-prophet: venv
	$(BIN)/python -m pip install -e ".[prophet]"

ingest:
	$(BIN)/python -m ovf_ingest run --days-back 7

ingest-full:
	$(BIN)/python -m ovf_ingest run --start 2026-01-01

climatology:
	$(BIN)/python -m ovf_ingest climatology --years 2016-2025

verify:
	$(BIN)/python -m ovf_ingest verify

forecast:
	$(BIN)/python -m ovf_forecast run

forecast-baseline:
	$(BIN)/python -m ovf_forecast run --model baseline

backtest:
	$(BIN)/python -m ovf_forecast backtest

report:
	$(BIN)/python -m ovf_forecast report

test:
	$(BIN)/python -m pytest

lint:
	$(BIN)/python -m ruff check .

typecheck:
	$(BIN)/python -m mypy

check: lint typecheck test

# Web (part 2). The build refuses to run on data older than 48 hours, so ingest and
# forecast have to have run first.
web-install:
	npm install

web-data:
	npm run data

web:
	npm run build

web-dev:
	npm run dev

web-preview:
	npm run preview

web-check:
	npm run check

web-test:
	npm test

web-e2e:
	npm run test:e2e

all: ingest forecast web

clean:
	rm -rf $(VENV) .mypy_cache .ruff_cache .pytest_cache
	rm -rf packages/web/dist packages/web/src/data packages/web/.astro
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

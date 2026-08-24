PYTHON ?= python3.12
VENV := .venv
BIN := $(VENV)/bin

.PHONY: help venv install ingest ingest-full climatology verify test lint typecheck check clean

help:
	@echo "make install      Create .venv and install the ingest + dev dependency groups"
	@echo "make ingest       Incremental run (--days-back 7)"
	@echo "make ingest-full  Full rebuild from 2026-01-01"
	@echo "make climatology  Fetch 10-year weather normals (run once)"
	@echo "make verify       Run the quality gates against data/processed without fetching"
	@echo "make test         pytest"
	@echo "make lint         ruff check"
	@echo "make typecheck    mypy"
	@echo "make check        lint + typecheck + test"

$(BIN)/python:
	$(PYTHON) -m venv $(VENV)

venv: $(BIN)/python

install: venv
	$(BIN)/python -m pip install --upgrade pip
	$(BIN)/python -m pip install -e ".[ingest,dev]"

ingest:
	$(BIN)/python -m ovf_ingest run --days-back 7

ingest-full:
	$(BIN)/python -m ovf_ingest run --start 2026-01-01

climatology:
	$(BIN)/python -m ovf_ingest climatology --years 2016-2025

verify:
	$(BIN)/python -m ovf_ingest verify

test:
	$(BIN)/python -m pytest

lint:
	$(BIN)/python -m ruff check .

typecheck:
	$(BIN)/python -m mypy

check: lint typecheck test

clean:
	rm -rf $(VENV) .mypy_cache .ruff_cache .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

.PHONY: help install demo test lint fixtures clean

help:
	@echo "make install    - install the package and dev tooling"
	@echo "make demo       - run the two-day scenario and print the brief"
	@echo "make test       - run the test suite"
	@echo "make lint       - ruff"
	@echo "make fixtures   - regenerate the synthetic fixture corpus"
	@echo "make clean      - remove generated output and snapshots"

install:
	python -m pip install -e ".[dev]"

demo:
	python -m regdelta.cli run --date 2026-08-04 --previous 2026-08-03

test:
	python -m pytest -q

lint:
	python -m ruff check src tests fixtures

fixtures:
	python fixtures/generate.py

clean:
	rm -rf output data .pytest_cache .ruff_cache .mypy_cache
	find . -name __pycache__ -type d -exec rm -rf {} +

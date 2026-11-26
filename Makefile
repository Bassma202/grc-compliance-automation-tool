.PHONY: setup test security demo up clean

UV := $(HOME)/.local/bin/uv
PYTHON := .venv/bin/python

setup:
	$(UV) venv --python 3.12
	$(UV) pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest -v

security:
	$(PYTHON) -m ruff check src tests scripts --select E9,F63,F7,F82
	$(PYTHON) -m bandit -r src scripts --severity-level high

demo:
	$(PYTHON) scripts/run_conserva_demo.py

up:
	$(PYTHON) -m uvicorn conserva.web:app --host 127.0.0.1 --port 8003

clean:
	rm -rf data/*.db .pytest_cache

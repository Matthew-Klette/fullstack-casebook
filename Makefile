PY ?= python3
VENV := api/.venv
PYBIN := $(VENV)/bin
.DEFAULT_GOAL := help

help:
	@echo "make setup      create the API virtualenv and install web dependencies"
	@echo "make dev        run API (8000), payroll stub (9100) and web (5173)"
	@echo "make test       api pytest, web vitest, contract check, e2e (Playwright Chromium)"
	@echo "make lint       ruff + tsc"
	@echo "make types      regenerate api/openapi.json and web/src/api/schema.d.ts"
	@echo "make prove CASE=N   show a case's regression test failing on its seed commit"

setup: $(PYBIN)/uvicorn web/node_modules

$(PYBIN)/uvicorn: api/requirements-dev.txt api/requirements.txt
	$(PY) -m venv $(VENV)
	$(PYBIN)/pip install -q -r api/requirements-dev.txt
	@touch $@

web/node_modules: web/package.json
	cd web && npm install --no-audit --no-fund
	@touch $@

dev: setup
	cd api && $(abspath $(PYBIN))/python -m app.seed
	@trap 'kill 0' INT TERM EXIT; \
	(cd api && $(abspath $(PYBIN))/python -m app.integrations.payroll_stub --port 9100) & \
	(cd api && $(abspath $(PYBIN))/python -m uvicorn app.main:app_factory --factory --reload --port 8000) & \
	(cd web && npm run dev) & \
	wait

test: test-api test-web contract test-e2e

test-api: setup
	cd api && $(abspath $(PYBIN))/python -m pytest -q

test-web: setup
	cd web && npx vitest run

contract: setup
	cd api && $(abspath $(PYBIN))/python -m pytest -q tests/test_contract.py
	cd web && npx vitest run src/contract.test.ts

test-e2e: setup
	cd web && npx playwright install chromium
	cd web && npx playwright test

screenshot: setup
	cd web && SCREENSHOT=1 npx playwright test -g "completes a shift"

lint: setup
	cd api && $(abspath $(PYBIN))/ruff check . && $(abspath $(PYBIN))/ruff format --check .
	cd web && npx tsc --noEmit

types: setup
	cd api && $(abspath $(PYBIN))/python -m scripts.dump_openapi
	cd web && npm run --silent gen:types

prove: setup
	./scripts/prove-case.sh $(CASE)

.PHONY: screenshot help setup dev test test-api test-web contract test-e2e lint types prove

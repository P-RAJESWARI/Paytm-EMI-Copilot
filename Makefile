# Developer commands for EMI-at-Counter Copilot. `make help` lists them.
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help
.NOTPARALLEL:

# Optional local overrides (see .env.example); exported so Compose, uvicorn and pytest see them.
-include .env
export

BACKEND_DIRECTORY := backend
BACKEND_HOST ?= 127.0.0.1
BACKEND_PORT ?= 8000
UV_RUN := uv run --locked
# Checks, types and tests run with the optional "ai" extra, so the LangGraph runner is covered too;
# core-without-langgraph proves the core still runs with LangGraph blocked (CLAUDE.md D5).
UV_RUN_WITH_AI := uv run --locked --extra ai
DATABASE_WAIT_TIMEOUT_IN_SECONDS := 90
OVERALL_COVERAGE_MINIMUM_PERCENT := 85

FRONTEND_DIRECTORY := frontend
PNPM := pnpm --dir $(FRONTEND_DIRECTORY)
OPENAPI_DOCUMENT := $(BACKEND_DIRECTORY)/openapi.json
GENERATED_API_SCHEMA := $(FRONTEND_DIRECTORY)/packages/api-client/src/generated/backendApiSchema.ts
# openapi-check writes its fresh exports here (git-ignored) and overwrites them on every run.
OPENAPI_CHECK_DIRECTORY := $(FRONTEND_DIRECTORY)/node_modules/.openapi-check

# End-to-end run (make e2e): its own database in the Compose PostgreSQL and its own ports, so it
# never touches the development database or the servers on 8000/5173 (and 8001/5174 for Layer 3).
E2E_DATABASE_NAME := emi_copilot_e2e
E2E_BACKEND_PORT := 8010
E2E_MERCHANT_WEB_PORT := 5180
E2E_CUSTOMER_WEB_PORT := 5181
# A throwaway pairing PIN for the throwaway e2e database only; never a real shop's PIN.
E2E_MERCHANT_PIN := 123456
E2E_POSTGRES_USER := $(or $(POSTGRES_USER),emi_copilot)
# pragma: allowlist nextline secret
E2E_POSTGRES_PASSWORD := $(or $(POSTGRES_PASSWORD),emi_copilot_local_only)
E2E_POSTGRES_HOST_PORT := $(or $(POSTGRES_HOST_PORT),55432)
E2E_DATABASE_URL := postgresql+psycopg://$(E2E_POSTGRES_USER):$(E2E_POSTGRES_PASSWORD)@localhost:$(E2E_POSTGRES_HOST_PORT)/$(E2E_DATABASE_NAME)
E2E_BACKEND_ENVIRONMENT := DATABASE_URL='$(E2E_DATABASE_URL)' PAYMENT_GATEWAY_MODE=mock

# Per-path coverage gates (testing.md section 5, ADR 0007) as <path under backend/>:<minimum %>.
# A gate is skipped until its path holds Python modules, so early steps stay green.
COVERAGE_GATES := \
	src/emi_copilot/domain:100 \
	src/emi_copilot/core:100 \
	src/emi_copilot/events/audit_subscriber.py:100 \
	src/emi_copilot/repositories/audit_event_repository.py:100 \
	src/emi_copilot/services:90 \
	src/emi_copilot/adapters:90

.PHONY: help setup dev db-up db-down db-reset lint typecheck test test-with-coverage coverage-gates \
	core-without-langgraph \
	check migrate seed demo openapi openapi-check frontend-setup frontend-check e2e-setup e2e

help: ## List the available commands
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-20s %s\n", $$1, $$2}'

setup: ## Install the locked Python dependencies and the git pre-commit hooks
	cd $(BACKEND_DIRECTORY) && uv sync --locked --extra ai
	cd $(BACKEND_DIRECTORY) && $(UV_RUN) pre-commit install

dev: db-up ## Start PostgreSQL and the API with auto-reload on BACKEND_HOST:BACKEND_PORT
	cd $(BACKEND_DIRECTORY) && $(UV_RUN) uvicorn emi_copilot.main:create_application --factory \
		--reload --host $(BACKEND_HOST) --port $(BACKEND_PORT)

db-up: ## Start PostgreSQL and wait until it is healthy (needs Docker, ADR 0007)
	@command -v docker > /dev/null 2>&1 || { \
		echo "ERROR: the docker CLI is not installed. PostgreSQL runs in Docker Compose (ADR 0007)." >&2; \
		exit 1; }
	@docker info > /dev/null 2>&1 || { \
		echo "ERROR: Docker is not running. Start Docker (or your Podman machine) and retry;" >&2; \
		echo "       make check needs the Compose PostgreSQL service (ADR 0007)." >&2; \
		exit 1; }
	docker compose up --detach --wait --wait-timeout $(DATABASE_WAIT_TIMEOUT_IN_SECONDS) postgres

db-down: ## Stop PostgreSQL, keeping its data volume
	docker compose down

lint: ## Run ruff lint and format checks
	cd $(BACKEND_DIRECTORY) && $(UV_RUN) ruff check .
	cd $(BACKEND_DIRECTORY) && $(UV_RUN) ruff format --check .

typecheck: ## Run mypy in strict mode
	cd $(BACKEND_DIRECTORY) && $(UV_RUN_WITH_AI) mypy

test: db-up ## Run every test level against the Compose PostgreSQL
	cd $(BACKEND_DIRECTORY) && $(UV_RUN_WITH_AI) pytest

test-with-coverage: db-up ## Run every test with branch coverage and the overall gate
	cd $(BACKEND_DIRECTORY) && $(UV_RUN_WITH_AI) pytest --cov --cov-report=term-missing \
		--cov-fail-under=$(OVERALL_COVERAGE_MINIMUM_PERCENT)

core-without-langgraph: ## Build the app and run the explanation flow with langgraph and langchain* imports blocked
	cd $(BACKEND_DIRECTORY) && AI_FLOW_RUNNER=sequential $(UV_RUN_WITH_AI) python -I \
		scripts/check_core_without_langgraph.py

coverage-gates: ## Enforce per-directory coverage minimums on the last coverage run
	@cd $(BACKEND_DIRECTORY) && for coverage_gate in $(COVERAGE_GATES); do \
		gate_path="$${coverage_gate%:*}"; gate_minimum_percent="$${coverage_gate##*:}"; \
		if [ -f "$$gate_path" ]; then include_pattern="*/$$gate_path"; \
		elif [ -d "$$gate_path" ] && [ -n "$$(find "$$gate_path" -name '*.py' ! -name '__init__.py' -print -quit)" ]; then \
			include_pattern="*/$$gate_path/*"; \
		else echo "Coverage gate skipped: $$gate_path has no modules yet"; continue; fi; \
		echo "Coverage gate: $$gate_path must be at least $$gate_minimum_percent%"; \
		$(UV_RUN) coverage report --include="$$include_pattern" --fail-under="$$gate_minimum_percent"; \
	done

check: lint typecheck core-without-langgraph db-up test-with-coverage coverage-gates frontend-check ## Backend and frontend lint, types, tests and coverage gates; must pass before every commit

frontend-setup: ## Install the locked frontend dependencies (Node 20 from frontend/.nvmrc, pnpm 12)
	$(PNPM) install --frozen-lockfile

frontend-check: ## Frontend type-check, ESLint (zero warnings), Prettier check and Vitest with axe and coverage
	@test -d $(FRONTEND_DIRECTORY)/node_modules || { \
		echo "ERROR: the frontend dependencies are not installed. Run make frontend-setup first." >&2; \
		exit 1; }
	$(PNPM) run check

migrate: db-up ## Apply all Alembic migrations to the development database
	cd $(BACKEND_DIRECTORY) && $(UV_RUN) alembic upgrade head

db-reset: db-up ## Drop every table of the development database and migrate again (demo data is lost)
	cd $(BACKEND_DIRECTORY) && $(UV_RUN) alembic downgrade base
	cd $(BACKEND_DIRECTORY) && $(UV_RUN) alembic upgrade head

seed: migrate ## Create the demo shop RAVI-0193, its products and (once) this week's report history; needs DEMO_MERCHANT_PIN
	cd $(BACKEND_DIRECTORY) && $(UV_RUN) python -m scripts.seed_demo_data

demo: seed ## Seed, then run the API (one worker, no reload) with the labelled MockCustomerSimulator on
	cd $(BACKEND_DIRECTORY) && MOCK_CUSTOMER_SIMULATOR_ENABLED=true $(UV_RUN) uvicorn \
		emi_copilot.main:create_application --factory --workers 1 \
		--host $(BACKEND_HOST) --port $(BACKEND_PORT)

openapi: ## Export and validate backend/openapi.json, then regenerate the api-client types (commit both)
	cd $(BACKEND_DIRECTORY) && $(UV_RUN) python scripts/export_openapi.py
	$(PNPM) run generate:api

openapi-check: ## Fail if backend/openapi.json or the generated api-client differs from a fresh export
	@test -d $(FRONTEND_DIRECTORY)/node_modules || { \
		echo "ERROR: the frontend dependencies are not installed. Run make frontend-setup first." >&2; \
		exit 1; }
	@mkdir -p $(OPENAPI_CHECK_DIRECTORY)
	@cd $(BACKEND_DIRECTORY) && $(UV_RUN) python -c 'import sys; \
		from emi_copilot.api.openapi_export import render_openapi_document; \
		sys.stdout.write(render_openapi_document())' > $(CURDIR)/$(OPENAPI_CHECK_DIRECTORY)/openapi.json
	@diff -u $(OPENAPI_DOCUMENT) $(OPENAPI_CHECK_DIRECTORY)/openapi.json > /dev/null || { \
		echo "ERROR: $(OPENAPI_DOCUMENT) is out of date. Run make openapi and commit the result." >&2; \
		exit 1; }
	@$(PNPM) --filter @emi-copilot/api-client exec openapi-typescript \
		$(CURDIR)/$(OPENAPI_CHECK_DIRECTORY)/openapi.json \
		--output $(CURDIR)/$(OPENAPI_CHECK_DIRECTORY)/backendApiSchema.ts > /dev/null 2>&1
	@diff -u $(GENERATED_API_SCHEMA) $(OPENAPI_CHECK_DIRECTORY)/backendApiSchema.ts > /dev/null || { \
		echo "ERROR: $(GENERATED_API_SCHEMA) is out of date. Run make openapi and commit the result." >&2; \
		exit 1; }
	@echo "OpenAPI document and generated api-client are up to date."

e2e-setup: ## Download Playwright's Chromium once (the only network use of the end-to-end tests)
	$(PNPM) --filter @emi-copilot/e2e exec playwright install chromium

e2e: db-up ## Recreate, migrate and seed the e2e database, then run the Playwright merchant and customer paths (ports 8010, 5180, 5181)
	@test -d $(FRONTEND_DIRECTORY)/node_modules || { \
		echo "ERROR: the frontend dependencies are not installed. Run make frontend-setup first." >&2; \
		exit 1; }
	docker compose exec -T postgres dropdb --username=$(E2E_POSTGRES_USER) --if-exists --force $(E2E_DATABASE_NAME)
	docker compose exec -T postgres createdb --username=$(E2E_POSTGRES_USER) $(E2E_DATABASE_NAME)
	cd $(BACKEND_DIRECTORY) && $(E2E_BACKEND_ENVIRONMENT) $(UV_RUN) alembic upgrade head
	cd $(BACKEND_DIRECTORY) && $(E2E_BACKEND_ENVIRONMENT) DEMO_MERCHANT_PIN=$(E2E_MERCHANT_PIN) \
		$(UV_RUN) python -m scripts.seed_demo_data
	E2E_DATABASE_URL='$(E2E_DATABASE_URL)' E2E_MERCHANT_PIN=$(E2E_MERCHANT_PIN) \
		E2E_BACKEND_PORT=$(E2E_BACKEND_PORT) E2E_MERCHANT_WEB_PORT=$(E2E_MERCHANT_WEB_PORT) \
		E2E_CUSTOMER_WEB_PORT=$(E2E_CUSTOMER_WEB_PORT) \
		$(PNPM) --filter @emi-copilot/e2e run test:e2e

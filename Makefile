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
DATABASE_WAIT_TIMEOUT_IN_SECONDS := 90
OVERALL_COVERAGE_MINIMUM_PERCENT := 85

# Per-path coverage gates (testing.md section 5, ADR 0007) as <path under backend/>:<minimum %>.
# A gate is skipped until its path holds Python modules, so early steps stay green.
COVERAGE_GATES := \
	src/emi_copilot/domain:100 \
	src/emi_copilot/events/audit_subscriber.py:100 \
	src/emi_copilot/repositories/audit_event_repository.py:100 \
	src/emi_copilot/services:90 \
	src/emi_copilot/adapters:90

.PHONY: help setup dev db-up db-down lint typecheck test test-with-coverage coverage-gates check migrate

help: ## List the available commands
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-20s %s\n", $$1, $$2}'

setup: ## Install the locked Python dependencies and the git pre-commit hooks
	cd $(BACKEND_DIRECTORY) && uv sync --locked
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
	cd $(BACKEND_DIRECTORY) && $(UV_RUN) mypy

test: db-up ## Run every test level against the Compose PostgreSQL
	cd $(BACKEND_DIRECTORY) && $(UV_RUN) pytest

test-with-coverage: db-up ## Run every test with branch coverage and the overall gate
	cd $(BACKEND_DIRECTORY) && $(UV_RUN) pytest --cov --cov-report=term-missing \
		--cov-fail-under=$(OVERALL_COVERAGE_MINIMUM_PERCENT)

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

check: lint typecheck db-up test-with-coverage coverage-gates ## Lint, types, tests and coverage gates; must pass before every commit

migrate: db-up ## Apply all Alembic migrations to the development database
	cd $(BACKEND_DIRECTORY) && $(UV_RUN) alembic upgrade head

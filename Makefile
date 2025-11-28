.PHONY: help install install-dev run run-dev format lint lint-fix test test-cov clean docker-up docker-down docker-logs docker-dev-up docker-dev-down docker-dev-logs docker-dev-restart migration-create migration-upgrade migration-downgrade migration-current migration-history pre-commit-install pre-commit-run all

# Default target
.DEFAULT_GOAL := help

# Colors for help output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Available commands:$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

install: ## Install project dependencies
	uv sync

install-dev: ## Install project dependencies including dev dependencies
	uv sync --all-groups

run: ## Run the application in production mode
	uv run uvicorn src.main:app --host 0.0.0.0 --port 8000

run-dev: ## Run the application in development mode with auto-reload
	ENVIRONMENT=development uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

format: ## Format code using Ruff
	env -u FORCE_COLOR uv run nox -s fmt

test: ## Run tests using pytest
	env -u FORCE_COLOR uv run nox -s test

test-cov: ## Run tests with coverage report
	uv run pytest --cov=src --cov-report=html --cov-report=term

docker-dev-up: ## Start development Docker services
	docker-compose --env-file .env.development -f docker-compose.dev.yml up -d

docker-dev-down: ## Stop development Docker services
	docker-compose --env-file .env.development -f docker-compose.dev.yml down -v

docker-dev-logs: ## View development Docker services logs
	docker-compose --env-file .env.development -f docker-compose.dev.yml logs -f

docker-dev-restart: ## Restart development Docker services
	docker-compose --env-file .env.development -f docker-compose.dev.yml restart

docker-up: ## Start production Docker services
	docker-compose -f docker-compose.yml up -d

docker-down: ## Stop production Docker services
	docker-compose -f docker-compose.yml down

docker-logs: ## View production Docker services logs
	docker-compose -f docker-compose.yml logs -f

docker-restart: ## Restart production Docker services
	docker-compose -f docker-compose.yml restart

migration-create: ## Create a new migration (usage: make migration-create MESSAGE="migration message")
	@if [ -z "$(MESSAGE)" ]; then \
		echo "Error: MESSAGE is required. Usage: make migration-create MESSAGE=\"your message\""; \
		exit 1; \
	fi
	ENVIRONMENT=development uv run alembic revision --autogenerate -m "$(MESSAGE)"

migration-upgrade: ## Upgrade database to the latest migration
	ENVIRONMENT=development uv run alembic upgrade head

migration-downgrade: ## Downgrade database by one revision
	ENVIRONMENT=development uv run alembic downgrade -1

migration-current: ## Show current database revision
	ENVIRONMENT=development uv run alembic current

migration-history: ## Show migration history
	ENVIRONMENT=development uv run alembic history

pre-commit-install: ## Install pre-commit hooks
	uv run pre-commit install

pre-commit-run: ## Run pre-commit hooks on all files
	uv run pre-commit run --all-files

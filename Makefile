.PHONY: help up down restart logs test test-unit test-integration test-e2e test-coverage lint type clean migrate

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

restart: down up ## Restart all services

logs: ## Show logs for all services
	docker-compose logs -f

test: ## Run all tests (unit + integration)
	docker-compose run --rm pytest

test-unit: ## Run unit tests only
	docker-compose run --rm pytest -m unit

test-integration: ## Run integration tests only
	docker-compose run --rm pytest -m integration

test-e2e: ## Run E2E tests
	docker-compose run --rm pytest -m e2e

test-coverage: ## Run tests with coverage report
	docker-compose run --rm backend pytest --cov=app --cov-report=html --cov-report=term

lint: ## Run linter (ruff)
	docker-compose run --rm --entrypoint ruff backend check app tests

lint-fix: ## Run linter with auto-fix
	docker-compose run --rm --entrypoint ruff backend check --fix app tests

format: ## Format code with black
	docker-compose run --rm --entrypoint black backend app tests

format-check: ## Check code formatting
	docker-compose run --rm --entrypoint black backend --check app tests

type: ## Run type checker (mypy)
	docker-compose run --rm --entrypoint mypy backend app

clean: ## Clean up Docker resources
	docker-compose down -v
	docker system prune -f

migrate: ## Run database migrations
	docker-compose exec backend alembic upgrade head

migrate-create: ## Create a new migration (use NAME=migration_name)
	docker-compose exec backend alembic revision --autogenerate -m "$(NAME)"

shell-backend: ## Open shell in backend container
	docker-compose exec backend /bin/bash

shell-db: ## Open PostgreSQL shell
	docker-compose exec db psql -U cb -d cbdb

docs-generate: ## Generate documentation (ERD, DDL)
	docker-compose run --rm backend python scripts/generate_erd.py
	@echo "Documentation generated:"
	@echo "  - backend/erd.md"
	@echo "  - backend/schema.sql"

docs-view: ## View documentation index
	@echo "Documentation Index:"
	@echo "  - docs/README.md - Main documentation index"
	@echo "  - docs/runbook.md - Operations runbook"
	@echo "  - docs/deployment.md - Deployment guide"
	@echo "  - CHANGELOG.md - Change history"
	@echo "  - backend/erd.md - Entity Relationship Diagram"
	@echo "  - backend/openapi.yaml - OpenAPI specification"

ci: lint format-check type test ## Run all CI checks locally


ifneq (,$(wildcard .env))
    include .env
    export
endif

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## Install dependencies
	poetry install

.PHONY: run
run: ## Run the whole stack (api, worker, beat, postgres, redis)
	docker compose up --build

.PHONY: migrate
migrate: ## Apply database migrations
	poetry run yimba db-upgrade

.PHONY: logs
logs: ## View logs from one/all containers (s=<service>)
	docker compose logs -f $(s)

.PHONY: down
down: ## Stop the stack and remove containers and networks
	docker compose down

.PHONY: lint
lint: ## Format check and lint
	poetry run black --check src tests migrations analytics
	poetry run isort --check src tests migrations analytics
	poetry run flake8 src tests migrations/env.py analytics

.PHONY: lint-arch
lint-arch: ## Check the architecture rules (import-linter)
	poetry run lint-imports

.PHONY: tests
tests: ## Run tests (set TEST_DATABASE_URL to run them on PostgreSQL)
	poetry run pytest -v

.PHONY: check
check: lint lint-arch tests ## Everything CI runs

.PHONY: analytics
analytics: ## Build and test the dbt marts, then run the Pandera quality checks
	docker compose --profile analytics run --rm --build analytics

.PHONY: dashboards
dashboards: ## Start Apache Superset (http://localhost:8088)
	docker compose --profile dashboards up -d --build

.PHONY: annotation
annotation: ## Start Label Studio (http://localhost:8080)
	docker compose --profile annotation up -d

.PHONY: mlflow
mlflow: ## Start the MLflow tracking server (http://localhost:5000)
	docker compose --profile ml up -d

.PHONY: observability
observability: ## Start GlitchTip (http://localhost:8000)
	docker compose --profile observability up -d

.PHONY: pre-commit
pre-commit: ## Run pre-commit
	pre-commit run --all-files

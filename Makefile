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
	poetry run black --check src tests migrations
	poetry run isort --check src tests migrations
	poetry run flake8 src tests migrations/env.py

.PHONY: lint-arch
lint-arch: ## Check the architecture rules (import-linter)
	poetry run lint-imports

.PHONY: tests
tests: ## Run tests (set TEST_DATABASE_URL to run them on PostgreSQL)
	poetry run pytest -v

.PHONY: check
check: lint lint-arch tests ## Everything CI runs

.PHONY: pre-commit
pre-commit: ## Run pre-commit
	pre-commit run --all-files

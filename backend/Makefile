# Backend commands, run from backend/ (the root Makefile delegates to these).
.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## Install dependencies (main and dev)
	poetry install

.PHONY: lint
lint: ## Format check and lint
	poetry run black --check yimba tests migrations
	poetry run isort --check yimba tests migrations
	poetry run flake8 yimba tests migrations/env.py

.PHONY: lint-arch
lint-arch: ## Check the architecture rules (import-linter)
	poetry run lint-imports

.PHONY: tests
tests: ## Run tests (set TEST_DATABASE_URL to run them on PostgreSQL)
	poetry run pytest -v

.PHONY: check
check: lint lint-arch tests ## Everything the backend CI runs

.PHONY: migrate
migrate: ## Apply database migrations
	poetry run yimba db-upgrade

.PHONY: api
api: ## Run the API with auto-reload (http://localhost:8800)
	poetry run yimba api --reload

ifneq (,$(wildcard .env))
    include .env
    export
endif

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ---- the whole stack (docker compose) ----------------------------------------------------------------------------

.PHONY: run
run: ## Run the whole stack (api, worker, beat, flower, postgres, redis)
	docker compose up --build

.PHONY: logs
logs: ## View logs from one/all containers (s=<service>)
	docker compose logs -f $(s)

.PHONY: down
down: ## Stop the stack and remove containers and networks
	docker compose down

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

# ---- development (each application has its own Makefile) ---------------------------------------------------------

.PHONY: install
install: ## Install the backend dependencies
	$(MAKE) -C backend install

.PHONY: migrate
migrate: ## Apply database migrations (backend)
	$(MAKE) -C backend migrate

.PHONY: lint
lint: ## Format check and lint (backend, analytics)
	$(MAKE) -C backend lint
	cd backend && poetry run black --config pyproject.toml --check ../analytics
	cd backend && poetry run isort --settings-path . --check ../analytics
	cd backend && poetry run flake8 --config .flake8 ../analytics

.PHONY: tests
tests: ## Run the backend tests (set TEST_DATABASE_URL to run them on PostgreSQL)
	$(MAKE) -C backend tests

.PHONY: check
check: lint ## Everything CI runs on the backend
	$(MAKE) -C backend lint-arch tests

.PHONY: pre-commit
pre-commit: ## Run pre-commit
	pre-commit run --all-files

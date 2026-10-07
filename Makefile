ifneq (,$(wildcard .env))
    include .env
    export
endif

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: run
# The application containers are recreated on every run; PostgreSQL and Redis only when their configuration changes:
# recreating Redis empties the task queue and cuts off the workers and Flower ("Error 111 connecting to redis:6379").
APP_SERVICES := migrate api worker beat frontend

run: ## Run the stack (web interface, api, worker, beat, postgres, redis); optional services: make help
	docker compose up -d --wait postgres redis
	docker compose up -d --build --force-recreate --no-deps $(APP_SERVICES)

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

.PHONY: monitoring
monitoring: ## Start Flower, the Celery web UI (http://localhost:5555)
	docker compose --profile monitoring up -d

.PHONY: observability
observability: ## Start GlitchTip (http://localhost:8000)
	docker compose --profile observability up -d

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

.PHONY: front-install
front-install: ## Install the frontend dependencies (pnpm)
	$(MAKE) -C frontend install

.PHONY: front-dev
front-dev: ## Frontend user app with hot reload (http://localhost:5173), against the API of the stack
	$(MAKE) -C frontend dev-user

.PHONY: front-dev-admin
front-dev-admin: ## Frontend admin app with hot reload (http://localhost:5174/admin)
	$(MAKE) -C frontend dev-admin

.PHONY: front-check
front-check: ## Everything CI runs on the frontend
	$(MAKE) -C frontend check

.PHONY: pre-commit
pre-commit: ## Run pre-commit
	pre-commit run --all-files

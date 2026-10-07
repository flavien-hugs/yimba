.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## Install the dependencies from the lockfile
	pnpm install --frozen-lockfile

.PHONY: dev-user
dev-user: ## User app on http://localhost:5173 (API: YIMBA_API_URL, default http://localhost:8800)
	pnpm dev:user

.PHONY: dev-admin
dev-admin: ## Admin app on http://localhost:5174/admin
	pnpm dev:admin

.PHONY: lint
lint: ## Formatting (Prettier)
	pnpm lint

.PHONY: format
format: ## Format the code (Prettier)
	pnpm format

.PHONY: tests
tests: ## Unit tests (Vitest)
	pnpm test

.PHONY: check
check: lint ## Everything CI runs: formatting, types, tests, build
	pnpm check
	pnpm test
	pnpm build

.PHONY: build
build: ## Build both apps (apps/*/build)
	pnpm build

.PHONY: api-types
api-types: ## Regenerate the API types from the running backend (OPENAPI_URL, default http://localhost:8800/openapi.json)
	pnpm api:types

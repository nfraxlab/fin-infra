.PHONY: help install setup run clean shell update test-providers

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies with Poetry
	poetry lock --no-update 2>/dev/null || poetry lock
	poetry install

setup: install ## Complete project setup (scaffold models + migrations)
	@echo " Setting up fin-infra template project..."
	@if [ ! -f .env ]; then \
		echo " Creating .env from .env.example..."; \
		cp .env.example .env; \
	fi
	@echo "🏗  Running scaffolding and migrations..."
	python3 scripts/quick_setup.py
	@echo ""
	@echo "[OK] Setup complete! Next steps:"
	@echo "   1. Review .env and configure provider credentials"
	@echo "   2. Enable desired providers (banking, market data, etc.)"
	@echo "   3. Run: make run"
	@echo ""

run: ## Start the development server
	@if [ ! -f .env ]; then \
		echo " Creating .env from .env.example..."; \
		cp .env.example .env; \
	fi
	@if [ ! -d "migrations" ]; then \
		echo ""; \
		echo "[!]  No database migrations found!"; \
		echo "   Run 'make setup' first to scaffold models and initialize the database."; \
		echo ""; \
		exit 1; \
	fi
	./run.sh

clean: ## Clean up cache files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

shell: ## Open a Poetry shell
	poetry shell

update: ## Update dependencies
	poetry update

test-providers: ## Test provider connections
	@echo " Testing provider connections..."
	python3 scripts/test_providers.py

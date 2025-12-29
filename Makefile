SHELL := /bin/bash
RMI ?= all

# Default for make pr sync flag
sync ?= 0

.PHONY: help accept compose_up wait seed down pytest_accept unit unitv integration integrationv clean clean-pycache test lint type typecheck format format-check check ci setup-template run-template _poetry-check

DC_FILE := docker-compose.test.yml
COMPOSE := docker compose -f $(DC_FILE)

# --- Poetry check helper ---
_poetry-check:
	@command -v poetry >/dev/null 2>&1 || { echo "[error] Poetry is not installed. Please install Poetry (https://python-poetry.org/docs/#installation)"; exit 2; }

help: ## Show available commands
	@echo "Available commands:"
	@echo ""
	@echo "Template Example:"
	@echo "  setup-template    Set up the example template (first time only)"
	@echo "  run-template      Run the fin-infra-template example server"
	@echo ""
	@echo "Testing:"
	@echo "  unit              Run unit tests (quiet)"
	@echo "  unitv             Run unit tests (verbose)"
	@echo "  integration       Run integration tests (quiet)"
	@echo "  integrationv      Run integration tests (verbose)"
	@echo "  accept            Run acceptance tests"
	@echo "  test              Run all tests (unit + integration + acceptance)"
	@echo ""
	@echo "Code Quality:"
	@echo "  format            Format code with black and isort"
	@echo "  format-check      Check formatting (black/isort)"
	@echo "  lint              Lint code with flake8 and ruff"
	@echo "  type              Type check with mypy"
	@echo "  typecheck         Alias for 'type'"
	@echo "  check             Run lint + type checks"
	@echo "  ci                Run checks + tests"
	@echo ""
	@echo "Docker Compose:"
	@echo "  compose_up        Start test services (if COMPOSE_PROFILES set)"
	@echo "  down              Tear down test services"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean             Remove caches, build artifacts, logs"
	@echo "  clean-pycache     Remove only __pycache__ directories"
	@echo ""

# --- Acceptance ---
compose_up:
	@if [ -n "$$COMPOSE_PROFILES" ]; then \
		echo "[accept] Starting services with profiles=$$COMPOSE_PROFILES"; \
		$(COMPOSE) up -d --wait; \
	else \
		echo "[accept] No external services requested (set COMPOSE_PROFILES=redis to enable Redis)"; \
	fi

wait:
	@if [ -n "$$COMPOSE_PROFILES" ]; then \
		echo "[accept] Waiting for services (redis)"; \
		poetry run python examples/scripts/wait_for.py 127.0.0.1 6379 20 || exit $$?; \
	else \
		echo "[accept] Nothing to wait for in library mode"; \
	fi

seed:
	@echo "[accept] No DB seed step — skipping seed"

pytest_accept: _poetry-check
	@echo "[accept] Running acceptance tests locally (marked with 'acceptance')"
	@poetry install --no-interaction --only main,dev >/dev/null 2>&1 || true
	@poetry run pytest -q -m acceptance

accept:
	@echo "[accept] Running acceptance (library mode)"
	@status=0; \
	$(MAKE) compose_up || status=$$?; \
	if [ $$status -eq 0 ]; then \
		$(MAKE) wait || status=$$?; \
	fi; \
	if [ $$status -eq 0 ]; then \
		$(MAKE) seed || status=$$?; \
	fi; \
	if [ $$status -eq 0 ]; then \
		$(MAKE) pytest_accept || status=$$?; \
	fi; \
	if [ $$status -eq 0 ]; then \
		echo "[accept] Acceptance complete"; \
	else \
		echo "[accept] Acceptance failed"; \
	fi; \
	exit $$status

down:
	@if [ -n "$$COMPOSE_PROFILES" ]; then \
		echo "[accept] Tearing down services"; \
		$(COMPOSE) down -v; \
	else \
		echo "[accept] Nothing to tear down"; \
	fi

# --- Unit tests ---
unit: _poetry-check
	@echo "[unit] Running unit tests (quiet)"
	@poetry install --no-interaction --only main,dev >/dev/null 2>&1 || true
	@poetry run pytest -q tests/unit

unitv: _poetry-check
	@echo "[unit] Running unit tests (verbose)"
	@poetry install --no-interaction --only main,dev >/dev/null 2>&1 || true
	@poetry run pytest -vv tests/unit

# --- Integration tests ---
integration: _poetry-check
	@echo "[integration] Running integration tests (quiet)"
	@poetry install --no-interaction --only main,dev >/dev/null 2>&1 || true
	@poetry run pytest -q tests/integration

integrationv: _poetry-check
	@echo "[integration] Running integration tests (verbose)"
	@poetry install --no-interaction --only main,dev >/dev/null 2>&1 || true
	@poetry run pytest -vv tests/integration

# --- Code Quality ---
format: _poetry-check
	@echo "[format] Formatting with black and isort"
	@poetry install --no-interaction --only dev >/dev/null 2>&1 || true
	@poetry run black . --line-length 100
	@poetry run isort . --profile black --line-length 100

format-check: _poetry-check
	@echo "[format] Checking formatting (black/isort)"
	@poetry install --no-interaction --only dev >/dev/null 2>&1 || true
	@poetry run black . --check --line-length 100
	@poetry run isort . --check-only --profile black --line-length 100

lint: _poetry-check
	@echo "[lint] Running flake8 and ruff on src/tests"
	@poetry install --no-interaction --only dev >/dev/null 2>&1 || true
	@poetry run flake8 --select=E,F src tests
	@poetry run ruff check src tests

type: _poetry-check
	@echo "[type] Running mypy"
	@poetry install --no-interaction --only dev >/dev/null 2>&1 || true
	@poetry run mypy src

typecheck: type

check: lint type
	@echo "[check] All checks passed"

ci: check test
	@echo "[ci] All checks + tests passed"

# --- Cleanup helpers ---
clean:
	@echo "[clean] Removing Python caches, build artifacts, and logs"
	@find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache build dist *.egg-info *.log
	@echo "[clean] Cleaning examples directory"
	@cd examples && rm -rf .pytest_cache .mypy_cache .ruff_cache build dist *.egg-info *.log 2>/dev/null || true

clean-pycache:
	@echo "[clean] Removing all __pycache__ directories recursively from project"
	@find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	@echo "[clean] Removing all __pycache__ directories recursively from examples"
	@cd examples && find . -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true

# --- Template example ---
setup-template:
	@echo "[template] Setting up fin-infra-template (install + scaffold + migrations)..."
	@cd examples && $(MAKE) setup

run-template:
	@echo "[template] Installing dependencies for fin-infra-template..."
	@cd examples && poetry install --no-interaction --quiet 2>/dev/null || true
	@echo "[template] Checking if setup has been run..."
	@if [ ! -d "examples/migrations" ]; then \
		echo ""; \
		echo "⚠️  Template not set up yet!"; \
		echo "   Run 'make setup-template' first to scaffold models and initialize the database."; \
		echo ""; \
		exit 1; \
	fi
	@echo "[template] Running fin-infra-template example..."
	@cd examples && env -i HOME="$$HOME" USER="$$USER" TERM="$$TERM" PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" bash -c 'exec ./run.sh'

# --- Combined test target ---
test:
	@echo "[test] Running unit, integration, and acceptance tests"
	@status=0; \
	$(MAKE) unit || status=$$?; \
	if [ $$status -eq 0 ]; then \
		$(MAKE) integration || status=$$?; \
	fi; \
	if [ $$status -eq 0 ]; then \
		$(MAKE) accept || status=$$?; \
	fi; \
	if [ $$status -eq 0 ]; then \
		echo "[test] All tests passed"; \
	else \
		echo "[test] Tests failed"; \
	fi; \
	exit $$status

# --- Docs Changelog ---
.PHONY: docs-changelog docs docs-serve docs-build

docs-changelog: ## Generate/update docs/CHANGELOG.json for What's New page
	@./scripts/docs-changelog.sh

docs: docs-serve ## Alias for docs-serve

docs-serve: ## Serve documentation locally with live reload
	@echo "[docs] Starting documentation server..."
	poetry run mkdocs serve

docs-build: ## Build documentation for production
	@echo "[docs] Building documentation..."
	poetry run mkdocs build

# --- Git/PR Automation ---
.PHONY: pr commit

# Usage:
#   make pr m="feat: add new feature"
#   make pr m="fix: bug" sync=1   # optional: rebase feature branch on origin/main before pushing
pr:
ifndef m
	$(error Usage: make pr m="feat: your commit message")
endif
	@set -euo pipefail; \
	if [ -z "$(m)" ]; then echo "[pr] ERROR: Commit message cannot be empty."; exit 1; fi; \
	FORCE_FLAG="$${FORCE:-0}"; \
	if ! echo "$(m)" | grep -qE '^(feat|fix|docs|chore|refactor|perf|test|ci|build)(\([^)]+\))?!?: .+'; then \
		if [ "$$FORCE_FLAG" != "1" ]; then \
			echo "[pr] ERROR: Commit message must follow Conventional Commits format."; \
			echo "    Expected: type(scope)?: description"; \
			echo "    Types: feat|fix|docs|chore|refactor|perf|test|ci|build"; \
			echo "    Example: feat: add new feature"; \
			echo "    Override with: make pr m=\"...\" FORCE=1"; \
			exit 1; \
		else \
			echo "[pr] WARNING: Non-conventional commit (FORCE=1 override)"; \
		fi; \
	fi; \
	gh auth status >/dev/null 2>&1 || { echo "[pr] ERROR: gh CLI not authenticated. Run 'gh auth login' first."; exit 1; }; \
	git remote get-url origin >/dev/null 2>&1 || { echo "[pr] ERROR: remote 'origin' not found."; exit 1; }; \
	DEFAULT_BRANCH=$$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's@^origin/@@' || echo main); \
	CURRENT_BRANCH=$$(git branch --show-current || true); \
	if [ -z "$$CURRENT_BRANCH" ]; then \
		echo "[pr] ERROR: Detached HEAD state. Checkout a branch first."; \
		exit 1; \
	fi; \
	SYNC_FLAG="$(sync)"; \
	if [ "$$SYNC_FLAG" != "1" ]; then SYNC_FLAG="0"; fi; \
	if [ "$$CURRENT_BRANCH" = "$$DEFAULT_BRANCH" ]; then \
		echo "[pr] On $$DEFAULT_BRANCH - creating new PR for: $(m)"; \
		TIMESTAMP=$$(date -u +%m%d%H%M%S); \
		RAND=$$(cat /dev/urandom 2>/dev/null | LC_ALL=C tr -dc 'a-z0-9' 2>/dev/null | head -c 4 || echo "0000"); \
		MSG_NO_PREFIX=$$(echo "$(m)" | sed -E 's/^[a-zA-Z]+(\([^)]+\))?!?:[ ]*//'); \
		SLUG=$$(echo "$$MSG_NO_PREFIX" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//' | sed 's/-$$//' | cut -c1-40); \
		[ -z "$$SLUG" ] && SLUG="change"; \
		BRANCH="$$SLUG-$$TIMESTAMP-$$RAND"; \
		git fetch origin "$$DEFAULT_BRANCH" >/dev/null; \
		git merge --ff-only "origin/$$DEFAULT_BRANCH" || { echo "[pr] ERROR: $$DEFAULT_BRANCH is not fast-forwardable. Resolve manually."; exit 1; }; \
		git checkout -b "$$BRANCH"; \
		git add -A; \
		if git diff --cached --quiet; then \
			echo "[pr] No changes to commit. Cleaning up branch."; \
			git checkout "$$DEFAULT_BRANCH" >/dev/null; \
			git branch -D "$$BRANCH" >/dev/null; \
			exit 0; \
		fi; \
		git commit -m "$(m)"; \
		git push --set-upstream origin "$$BRANCH"; \
		if gh pr view --head "$$BRANCH" >/dev/null 2>&1; then \
			echo "[pr] PR already exists: $$(gh pr view --head "$$BRANCH" --json url -q .url)"; \
		else \
			gh pr create --title "$(m)" --body "$(m)" --base "$$DEFAULT_BRANCH" --head "$$BRANCH"; \
		fi; \
		echo "[pr] PR: $$(gh pr view --head "$$BRANCH" --json url -q .url 2>/dev/null || true)"; \
		git checkout "$$DEFAULT_BRANCH" >/dev/null; \
		echo "[pr] Done!"; \
	else \
		echo "[pr] On branch $$CURRENT_BRANCH - updating/creating PR"; \
		PR_STATE=$$(gh pr view --head "$$CURRENT_BRANCH" --json state -q .state 2>/dev/null || echo "NONE"); \
		if [ "$$PR_STATE" = "MERGED" ]; then \
			echo "[pr] ERROR: PR for branch '$$CURRENT_BRANCH' was already MERGED."; \
			echo "    Your commits won't reach $$DEFAULT_BRANCH by pushing to this branch."; \
			echo ""; \
			echo "    Options:"; \
			echo "    1. Switch to $$DEFAULT_BRANCH and create a new PR:"; \
			echo "       git checkout $$DEFAULT_BRANCH && make pr m=\"$(m)\""; \
			echo ""; \
			echo "    2. Create a new branch from this one:"; \
			echo "       git checkout -b new-branch-name && make pr m=\"$(m)\""; \
			exit 1; \
		fi; \
		if [ "$$PR_STATE" = "CLOSED" ]; then \
			echo "[pr] WARNING: PR for branch '$$CURRENT_BRANCH' was CLOSED (not merged)."; \
			echo "    Will create a new PR after pushing."; \
		fi; \
		git fetch origin "$$DEFAULT_BRANCH" >/dev/null; \
		BEHIND=$$(git rev-list --count HEAD..origin/"$$DEFAULT_BRANCH" 2>/dev/null || echo 0); \
		if [ "$$BEHIND" -gt 0 ] && [ "$$SYNC_FLAG" != "1" ]; then \
			echo "[pr] WARNING: Branch is $$BEHIND commits behind origin/$$DEFAULT_BRANCH."; \
			echo "    Consider: make pr m=\"...\" sync=1"; \
		fi; \
		if [ "$$SYNC_FLAG" = "1" ]; then \
			echo "[pr] Sync enabled - rebasing $$CURRENT_BRANCH on origin/$$DEFAULT_BRANCH"; \
			git fetch origin "$$CURRENT_BRANCH" >/dev/null 2>&1 || true; \
			if git rev-parse --verify origin/"$$CURRENT_BRANCH" >/dev/null 2>&1; then \
				if ! git merge-base --is-ancestor origin/"$$CURRENT_BRANCH" HEAD; then \
					echo "[pr] ERROR: Remote branch has commits not in your local branch."; \
					echo "    Refusing to rebase/force-push. Pull/fetch and reconcile first."; \
					exit 1; \
				fi; \
			fi; \
			git rebase origin/"$$DEFAULT_BRANCH" || { echo "[pr] ERROR: Rebase failed. Run 'git rebase --abort' and resolve manually."; exit 1; }; \
		fi; \
		git add -A; \
		COMMITTED=0; \
		if git diff --cached --quiet; then \
			echo "[pr] No changes to commit"; \
		else \
			git commit -m "$(m)"; \
			COMMITTED=1; \
		fi; \
		AHEAD=0; \
		if git rev-parse --verify origin/"$$CURRENT_BRANCH" >/dev/null 2>&1; then \
			AHEAD=$$(git rev-list --count origin/"$$CURRENT_BRANCH"..HEAD 2>/dev/null || echo 0); \
		fi; \
		if [ "$$SYNC_FLAG" = "1" ]; then \
			git push --force-with-lease origin "$$CURRENT_BRANCH"; \
		elif [ "$$COMMITTED" = "1" ] || [ "$$AHEAD" -gt 0 ] || ! git rev-parse --verify origin/"$$CURRENT_BRANCH" >/dev/null 2>&1; then \
			git push -u origin "$$CURRENT_BRANCH"; \
		fi; \
		if gh pr view --head "$$CURRENT_BRANCH" >/dev/null 2>&1; then \
			echo "[pr] PR exists: $$(gh pr view --head "$$CURRENT_BRANCH" --json url -q .url)"; \
		else \
			gh pr create --title "$(m)" --body "$(m)" --base "$$DEFAULT_BRANCH" --head "$$CURRENT_BRANCH"; \
		fi; \
		echo "[pr] PR: $$(gh pr view --head "$$CURRENT_BRANCH" --json url -q .url 2>/dev/null || true)"; \
	fi

# Usage: make commit m="feat: add new feature"
# Just commits with proper message (for when you want to batch commits before PR)
commit:
ifndef m
	$(error Usage: make commit m="feat: your commit message")
endif
	git add -A
	git commit -m "$(m)"

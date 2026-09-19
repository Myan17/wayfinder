.PHONY: help setup test lint fmt authz eval load deploy digest hooks
help:            ## list targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/\t/' | expand -t22

hooks:           ## install the git hooks (per clone and per worktree)
	git config core.hooksPath .githooks
	@echo "hooks installed; set WAYFINDER_AGENT and git config wayfinder.operator"

setup:           ## create the dev environment
	uv sync --extra dev

test:            ## run the python test suite
	uv run pytest

authz:           ## run the blocking authorization suite (AGENTS.md 5, DESIGN 16.3)
	uv run pytest apps/api/tests/authz -v

lint:            ## lint and type-check
	uv run ruff check .
	uv run ruff format --check .

fmt:             ## format
	uv run ruff format .

guardrails:      ## run the collaboration guardrails against origin/main
	python3 scripts/check_commit_identity.py origin/main HEAD
	python3 scripts/check_ownership.py origin/main HEAD
	python3 scripts/check_agent_log.py origin/main HEAD
	python3 scripts/check_context_freshness.py
	python3 scripts/gen_codeowners.py --check

digest:          ## build this week's gate report from the task logs
	python3 scripts/weekly_digest.py

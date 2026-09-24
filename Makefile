.PHONY: help setup test lint fmt authz eval load deploy digest hooks db-up db-down db-test schema-check manifest-check
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

# The pinned ParadeDB image from spike S3 (infra/spikes/s3/compose.yml), shared by laptops and CI.
DB_COMPOSE := docker compose -p wf-schema -f infra/spikes/s3/compose.yml
export WAYFINDER_TEST_DSN ?= postgresql://wayfinder:spike_local_only_not_a_secret@localhost:55432/s3spike

db-up:           ## start the pinned ParadeDB and wait until it accepts a real query
	$(DB_COMPOSE) up -d --wait
	@# The compose healthcheck can report healthy while Postgres is still finishing first boot (#19).
	@for i in $$(seq 1 60); do \
	  $(DB_COMPOSE) exec -T paradedb psql -U wayfinder -d s3spike -qAtc 'select 1' >/dev/null 2>&1 && exit 0; \
	  sleep 1; done; echo "database never accepted a query" >&2; exit 1

db-down:         ## stop the pinned ParadeDB
	$(DB_COMPOSE) down

db-test:         ## schema tests against the pinned database (needs db-up); a skip is a failure
	@# db/tests skip without a database. Here a skip would turn a missing database into a green run,
	@# so any skipped test fails the target.
	@out="$$(uv run pytest db/tests -rs 2>&1)"; rc=$$?; echo "$$out"; \
	  [ $$rc -eq 0 ] || exit $$rc; \
	  if echo "$$out" | tail -1 | grep -q skipped; then echo "db-test: tests were skipped" >&2; exit 1; fi

schema-check:    ## fail if db/schema.sql differs from a fresh dump of the migrations
	db/dump-schema.sh --check

manifest-check:  ## validate the example release manifest and print its cache keys (DESIGN 16.9)
	python3 infra/manifest/release_manifest.py validate infra/manifest/example.json
	@for s in index eval; do python3 infra/manifest/release_manifest.py cache-key infra/manifest/example.json --scope $$s; done

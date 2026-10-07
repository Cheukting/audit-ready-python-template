.PHONY: help install lint format test cov adversarial tz types audit check build clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "} {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:  ## Create the dev environment and install the git hooks
	uv sync --all-groups
	uv run pre-commit install

lint:  ## ruff (lint + format check) and custom semgrep rules
	uv run ruff check .
	uv run ruff format --check .
	uv run --group semgrep semgrep --config .semgrep.yml --error --disable-version-check --quiet mypackage/ tests/

format:  ## Apply ruff formatting and safe fixes
	uv run ruff check --fix .
	uv run ruff format .

test:  ## Run the test suite (random order)
	uv run pytest

cov:  ## Run the test suite with the 100% coverage gate
	uv run pytest --cov --cov-report=term-missing

adversarial:  ## Run the adversarial suite with the CI Hypothesis profile
	HYPOTHESIS_PROFILE=ci uv run pytest -m adversarial --hypothesis-show-statistics

tz:  ## Run the suite under the timezones CI uses
	@for tz in UTC Asia/Tokyo America/Los_Angeles Asia/Kathmandu; do \
		echo "== TZ=$$tz"; TZ=$$tz uv run pytest -q || exit 1; done

types:  ## ty, mypy --strict, and import-linter contracts
	uv run ty check
	uv run mypy --strict mypackage/
	uv run lint-imports

audit:  ## Lockfile sync, known CVEs, workflow analysis
	uv lock --check
	uv export --frozen --no-dev --no-emit-project --format requirements-txt --quiet --output-file .requirements.audit.txt
	uv run --group tools pip-audit --strict --disable-pip --require-hashes --requirement .requirements.audit.txt
	@# Second run: every group (dev and tools included) against OSV. See ci.yml -> audit for why two runs.
	uv export --frozen --all-groups --no-emit-project --format requirements-txt --quiet --output-file .requirements.audit.txt
	uv run --group tools pip-audit --strict --disable-pip --require-hashes --vulnerability-service osv --requirement .requirements.audit.txt
	rm -f .requirements.audit.txt
	uv run --group tools zizmor --min-severity medium .github/workflows/

check: lint types cov adversarial audit  ## Everything CI runs (except the OS/TZ matrix)

build:  ## Build the sdist and wheel
	uv build

clean:  ## Remove build and cache artefacts
	rm -rf dist build .pytest_cache .ruff_cache .mypy_cache .hypothesis .coverage coverage.xml htmlcov junit.xml sbom.json
	find . -name __pycache__ -type d -prune -exec rm -rf {} +

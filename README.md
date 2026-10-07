# audit-ready-python-template

A Python project template that turns the hands-on part of the
**[Audit and evaluate AI generated code](https://github.com/Cheukting/audit-ai-workshop)**
workshop into defaults. Every recommendation from Exercises 1–4 is already set up and
passing, so a new project starts with the guardrails instead of adding them
after the first incident.

> Don't blindly trust AI-generated code. Review, test and validate it.
> This template makes the machines do as much of that as possible, so that the
> human review can focus on what only a human can judge.

`mypackage/` is a small, working example: a paginated HTTP client and CLI.
Every rule has real code to check, and you can see what "passing" looks like.
It includes a **fixed** version of the workshop's `fetch_with_retry`: it never
returns `None`, never retries a TLS failure, and never sleeps after the last attempt.

## Quick start

```bash
# 1. Use this template on GitHub (or clone it), then rename the package:
git grep -l mypackage | xargs sed -i '' 's/mypackage/yourpackage/g'   # GNU sed: drop the ''
git grep -l MYPACKAGE | xargs sed -i '' 's/MYPACKAGE/YOURPACKAGE/g'
git mv mypackage yourpackage
#    Then fix the handles in .github/CODEOWNERS and the authors in pyproject.toml.

# 2. Set up
make install        # uv sync --all-groups && pre-commit install

# 3. Run everything CI runs
make check
```

Then replace the example modules with your own code. Keep the layering idea,
and update `.importlinter` to match your modules.

## What's included, and where

### Exercise 1: Functional verification

| Recommendation | Where |
|---|---|
| Property-based testing with Hypothesis | `tests/test_properties.py`, `tests/test_adversarial.py` |
| `dev` / `ci` Hypothesis profiles (`HYPOTHESIS_PROFILE`) | `tests/conftest.py` |
| `pytest-randomly` (order dependence), `pytest-timeout` (hangs), `time-machine` (clock) | `pyproject.toml` `[dependency-groups]` |
| Coverage gate: 100% line + branch, enforced | `[tool.coverage.report] fail_under = 100` |
| Timezone matrix: `Asia/Tokyo`, `America/Los_Angeles`, `Asia/Kathmandu` (Windows keeps the default) | `.github/workflows/ci.yml` → `test` |

### Exercise 2: Security & audit

| Recommendation | Where |
|---|---|
| Expanded ruff rule set (`DTZ`, `RET`, `S`, `TRY`, `PL`, `D`, …) | `pyproject.toml` `[tool.ruff.lint]` |
| Custom semgrep rules (naive clock, shallow-copied defaults, retry-returns-`None`, broad `RequestException`, `verify=False`) | `.semgrep.yml` |
| semgrep in CI and in pre-commit, on `tests/` too | `ci.yml` → `lint`; `.pre-commit-config.yaml`; `.semgrepignore` |
| Lockfile in sync: `uv lock --check` | `ci.yml` → `audit` |
| Known CVEs in runtime deps: `pip-audit --strict` (PyPI DB) | `ci.yml` → `audit` |
| Known CVEs incl. dev deps: `pip-audit -s osv` on every locked group (OSV DB) | `ci.yml` → `audit` |
| Workflow static analysis: `zizmor` | `ci.yml` → `audit` |
| SBOM (CycloneDX, reproducible, contents checked) uploaded as an artefact | `ci.yml` → `audit` |
| Dependabot for update hygiene (**not** vulnerability auditing) | `.github/dependabot.yml` |

### Exercise 3: Adversarial review

| Recommendation | Where |
|---|---|
| Attack-class checklist and "break it yourself" commands | `docs/adversarial-review.md` |
| Write the threat model down | `THREAT_MODEL.md` |
| Fuzz the parsers | `tests/test_adversarial.py::test_fuzz_*` |
| Fault injection in CI | `test_fault_injection` + `ci.yml` → `adversarial` |
| A pathological fake next to the well-behaved one | `tests/fakes.py` |
| Two code-review rituals: *attack it*, and *red-team the fix, not just the bug* | `.github/pull_request_template.md` |

### Exercise 4: Architectural alignment

| Recommendation | Where |
|---|---|
| Type annotations everywhere, `mypy --strict` and `ty` | `mypackage/`, `ci.yml` → `types` |
| `TypedDict` config shape, `Final` defaults, deep copies | `mypackage/config.py` |
| Naive vs aware datetimes distinguished (`AwareDatetime` `NewType`) | `mypackage/clock.py`, `docs/adr/0001-*` |
| `Protocol`s for callables and collaborators | `retry.Fetch`, `clock.Clock`, `client.HttpSession` |
| `py.typed` shipped in the wheel (checked in CI) | `mypackage/py.typed`, `ci.yml` → `build` |
| Banned APIs (`utcnow`, `requests.get`, `pickle`, …), no relative imports | `pyproject.toml` `[tool.ruff.lint.flake8-tidy-imports]` |
| import-linter contracts: exhaustive layers (every module must be placed), `errors` is a leaf, only `client`/`retry` import `requests` | `.importlinter` |
| `ty` (and import-linter) in pre-commit | `.pre-commit-config.yaml` |

### Human in the loop

| Practice | Where |
|---|---|
| A human must approve every change, with extra owners for security surfaces | `.github/CODEOWNERS` |
| PR template: AI provenance, failure-path / security-signal / time / input checks | `.github/pull_request_template.md` |
| Rules for AI coding assistants | `AGENTS.md` (also read through `CLAUDE.md`) |
| Decisions an assistant must not "helpfully" undo | `docs/adr/` |

## CI jobs

| Job | What fails the build |
|---|---|
| `lint` | ruff, ruff format, semgrep custom rules |
| `test` | pytest (random order) on py3.11–3.14, Linux/macOS/Windows, 4 timezones; coverage < 100% |
| `adversarial` | fuzzing and fault injection with 1000 examples per property |
| `types` | `ty`, `mypy --strict`, import-linter contracts |
| `audit` | stale lockfile, known CVEs (runtime via PyPI, every group via OSV), ruff `S`, zizmor findings |
| `build` | `twine check --strict`, `py.typed` missing from the wheel |

Every action is pinned to a commit SHA, the workflow has `contents: read`
permissions, and checkout does not persist credentials.

## Differences from the workshop slides

Applying the slide snippets exactly as written turned up a few problems, which are fixed here:

- **import-linter**: `forbidden_modules = mypackage` (forbidding the root
  package) is silently a no-op, so the "errors is a leaf" contract never fails.
  This template forbids `mypackage.*` (the child modules) instead.
- **semgrep**: `pattern: dict($DEFAULTS)` matches every `dict(x)` call. Here it
  is narrowed with `metavariable-regex` to `UPPER_CASE` module constants.
- **semgrep** skips `tests/` by default, even when the directory is passed on the
  command line, so `semgrep mypackage/ tests/` scans only `mypackage/`. The
  `.semgrepignore` here replaces the default list, without its test paths.
- **osv-scanner** is a Go binary and is not on PyPI, so `uvx osv-scanner` does
  not work (and the PyPI package `osv` is an unrelated, archived project). Its
  GitHub Action loads a Docker image by mutable tag, so this template runs
  `pip-audit --vulnerability-service osv` on the `--all-groups` export instead.
- **pip-audit** uses `--disable-pip --require-hashes` with the hash-pinned
  `uv export`. Without `--disable-pip`, pip-audit installs the requirements into a
  temporary venv, which runs their build code; with it, nothing is installed. In
  this mode `--require-hashes` only checks that hashes are *present*, with either
  vulnerability service (a requirements file with every hash zeroed still passes),
  so hash validity is left to uv, which checks downloads against `uv.lock`.
- **cyclonedx-py**: `cyclonedx-py environment` with no path describes the Python
  running it. Under `uvx`, that is an SBOM of the tool itself: valid JSON, wrong
  contents. This template points it at the runtime-only `.venv`, passes
  `--pyproject` so the SBOM records `mypackage` as its subject, makes the output
  reproducible, and checks the contents in CI. (`uvx cyclonedx-py` works through an
  alias package; `--from cyclonedx-bom` installs the real package directly.)

## Recommended repository settings

These can't be set from a file:

- Branch protection on `main`: require PRs, require **1+ approving review from Code Owners**, require all CI jobs above to pass, and dismiss stale approvals when new commits are pushed.
- Enable Dependabot security alerts and secret scanning with push protection.
- Mark the repository as a **template repository** (Settings → General).

## Make targets

```text
make install      create the env and install git hooks
make check        lint + types + cov + adversarial + audit
make tz           run the suite under every CI timezone
make help         list everything
```

## Beyond this template: evaluating your AI workflow

The guardrails above check the *code*. To measure the *AI workflow* that
produces it (accuracy and consistency across runs, prompt variations, failure
patterns), see [DeepEval](https://deepeval.com),
[Ragas](https://docs.ragas.io/) and [Arize Phoenix](https://phoenix.arize.com/).

## License

MIT. See [LICENSE](LICENSE).

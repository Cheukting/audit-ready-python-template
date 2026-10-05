# Contributing

## Getting set up

```bash
make install        # uv sync --all-groups && pre-commit install
```

## Before opening a pull request

```bash
make check          # lint, types, coverage gate, adversarial suite, audit
make tz             # optional: the timezone matrix CI runs
```

Fill in the pull request template. It covers AI provenance and the two review rituals.

## Conventions

- Every public function has a docstring, including a `Raises:` section for its failure cases (ruff `D`).
- On failure, raise a typed error. Never return `None` or a default.
- Changes to behaviour come with tests: a property test for logic, and a
  `PathologicalUpstream` test for I/O. The suite needs no network or credentials.
- Fix a bug with a regression test, then try to break the fix ("red-team the fix").
- Record decisions in `docs/adr/` and threats in `THREAT_MODEL.md`.
- Add an entry under `## [Unreleased]` in `CHANGELOG.md`.

## Suppressions

`# noqa`, `# type: ignore`, `# nosemgrep: <rule-id>` and `pragma: no cover`
must name the specific rule and give a reason on the same line. Reviewers treat
an unexplained suppression as a bug.

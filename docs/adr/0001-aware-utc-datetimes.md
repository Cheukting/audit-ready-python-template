# ADR-0001: All datetimes are aware UTC

- Status: accepted

## Context

To the type system, naive and aware `datetime` values look the same. Comparing
them raises an error, and mixing them by accident (`datetime.now()` next to a
parsed `...Z` timestamp) causes bugs that only appear in some timezones. The CI
runner defaults to UTC, so those bugs pass CI and then fail in production.

## Decision

- `mypackage.clock` is the only module that reads the wall clock (`utc_now`).
- Values crossing a boundary are converted to `AwareDatetime` (a `NewType`).
  Naive input is rejected, never assumed to be UTC.
- This is enforced by ruff `DTZ` and the `banned-api` list, the semgrep rule
  `no-naive-utc-clock`, and a CI matrix with `TZ` set to Asia/Tokyo,
  America/Los_Angeles and Asia/Kathmandu.

## Consequences

Tests control time with `time-machine` and an injected `Clock`. If code
genuinely needs a naive datetime, it uses `# noqa: DTZ…` and gives a reason.

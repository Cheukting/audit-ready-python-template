# Architecture Decision Records

Record any decision that a reviewer, or an AI assistant, might otherwise
"helpfully" undo. Copy the newest ADR, give it the next number, and link it from the rule that enforces it.

| ADR | Decision | Enforced by |
|---|---|---|
| [0001](0001-aware-utc-datetimes.md) | All datetimes are aware UTC | ruff `DTZ`/`TID251`, semgrep, TZ matrix |

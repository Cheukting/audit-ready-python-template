# Threat model

> Write the threat model down. A threat model that only lives in someone's head
> cannot be reviewed, and an AI assistant cannot follow it.
> Update this file whenever a change adds an input, a dependency, or a trust boundary.

## Assets

| Asset | Why it matters |
|---|---|
| Correctness of the item listing | Downstream systems act on it (e.g. grant or revoke access) |
| TLS integrity of upstream traffic | Without it, an attacker on the network controls what we see |
| CI / release pipeline | A compromised workflow can publish malicious wheels |

## Trust boundaries and entry points

| Entry point | Trust | Where it is validated |
|---|---|---|
| CLI arguments | Untrusted (operator typos, scripts) | `cli.positive_int`, then `config.validate` |
| `MYPACKAGE_*` environment | Untrusted | `config.from_env` (strict parse), `config.validate` |
| Upstream HTTP responses | **Hostile** | `client.parse_page` / `parse_item`, `clock.parse_timestamp` |
| Network path to upstream | **Hostile** | TLS verification on, `SSLError` never retried |
| Wall clock / local timezone | Unreliable | Only read in `clock.utc_now`. Everything is aware UTC |
| Dependencies (`uv.lock`) | Supply chain | `audit` CI job (pip-audit against PyPI and OSV), SBOM artefact, Dependabot |
| CI tools (semgrep, pip-audit, zizmor, cyclonedx-bom, twine) | Supply chain | Locked and hash-pinned in `uv.lock` (`tools` / `semgrep` groups, not `uvx`), covered by the OSV audit, installed only in the jobs that run them |
| GitHub Actions workflows | Supply chain | SHA-pinned actions, least privilege, `zizmor` |

## Attack classes and our answers

| Attack class | Example | Mitigation | Test |
|---|---|---|---|
| Hostile upstream | non-JSON, wrong shapes, 10 MB ids | strict parsers, length bounds | `test_fuzz_parse_*`, `test_malformed_pages` |
| Pagination abuse | cursor loop, endless fresh cursors, oversize pages | `seen` set, `max_pages`, `page_size` check | `test_cursor_loop_*`, `test_endless_*`, `test_oversized_*` |
| Retry amplification | attacker forces failures to multiply load | bounded `retries` (1–10), backoff, no sleep after last try | `test_backoff_schedule` |
| Forced TLS failure | MITM to trigger the "failure → None → allow" path | `TransportSecurityError`, raised and never retried. No `None` path | `test_tls_failure_*` |
| The clock | naive timestamps, DST, odd offsets | aware-only `AwareDatetime`, TZ matrix in CI | `test_clock.py`, CI `tz` matrix |
| Config surface | `--retries -3`, `--page-size 0`, `retries=True`, NaN | argparse types, `config.validate` bounds | `test_config.py`, `test_usage_errors_exit_2` |
| Filesystem and process | (none yet. Add rows when the package writes files or spawns processes) | | |
| Concurrent writes during pagination | items added or removed between pages | **Accepted risk**: cursor pagination may skip or duplicate. Consumers must be idempotent | — |

## Accepted risks

- We trust the upstream's TLS certificate chain through the system CA store.
- Pagination is not a consistent snapshot (see above).

# Instructions for AI coding assistants

This repository assumes generated code looks right while being subtly wrong.
The checks below are enforced by CI. Follow them, and do not weaken them.

## Never

- Return `None` (or any sentinel) to signal failure. Raise a typed error from `mypackage/errors.py`.
- Catch `requests.exceptions.RequestException` (or `Exception`) around network
  calls without handling `SSLError` first. TLS failures are raised, not retried.
- Call `datetime.now()` / `utcnow()` / `strptime()` directly. Use `mypackage.clock`.
- Use `requests.get` / `requests.post`. Go through the client's `Session`.
- Copy config with `dict(DEFAULTS)`. Use `load_config()`, which deep-copies.
- Add `# noqa`, `# type: ignore`, `# nosemgrep`, `pragma: no cover`, or lower the
  coverage gate, unless a human asks for it. Always include a reason.
- Edit `.semgrep.yml`, `.semgrepignore`, `.importlinter`, `[tool.ruff]`, or CI workflows to make a check pass.

## Always

- Validate every external input (CLI, env, upstream JSON) at the boundary, with bounds.
- Add a property test (Hypothesis) for new logic, and an adversarial test using
  `tests/fakes.PathologicalUpstream` for new I/O.
- Keep the import layers in `.importlinter`. `errors` imports nothing.
- Run `make check` before saying the work is done, and report any failure exactly as it appeared.
- Update `THREAT_MODEL.md` when adding an input, a dependency, or a trust boundary.

## What and why

<!-- What does this change do, and why is it needed? Link the issue. -->

## Provenance

- [ ] Some or all of this change was AI-generated (tool/model: ______ )
- [ ] I have read every line and can explain it without the AI's help

## Human-in-the-loop review

AI-generated code tends to look right while being subtly wrong. A green
checkmark alone does not mean it is correct.

- [ ] **Failure paths**: on failure, it raises a typed error. It never returns `None` or a default that a caller could mistake for success.
- [ ] **Security signals**: TLS, auth and permission errors surface immediately. They are not retried, logged-and-ignored, or grouped with transient errors.
- [ ] **Time**: every datetime is aware UTC (via `mypackage.clock`). Nothing depends on the machine's timezone.
- [ ] **Inputs**: every value from outside (CLI, env, upstream JSON) is validated at the boundary, with bounds.
- [ ] **Tests assert behaviour**, not just that a line ran: properties for logic, a pathological fake for I/O.

## Adversarial review (the two rituals)

- [ ] **Attack it**: I tried to break this change with hostile input. What I tried: ______
- [ ] **Red-team the fix, not just the bug**: for a bug fix, I tried to break the fix itself, and added the attack to `tests/test_adversarial.py`.

## Checklist

- [ ] `make check` passes locally
- [ ] `THREAT_MODEL.md` updated if this adds a new input, dependency or trust boundary
- [ ] `CHANGELOG.md` entry under `## [Unreleased]`

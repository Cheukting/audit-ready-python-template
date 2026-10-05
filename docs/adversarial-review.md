# Adversarial review playbook

Try to break your own program before someone else does. Install it, attack
it, and **write down what happened**, what caused it, and the fix.

```bash
uv sync --all-groups
uv run mypackage --retries 0 config        # rejected: must be >= 1
uv run mypackage --retries -3 config       # rejected
uv run mypackage items --page-size 0       # rejected
uv run mypackage timestamp garbage         # error, exit 1
uv run mypackage timestamp 2026-01-01T00:00:00   # naive, so rejected
MYPACKAGE_RETRIES=lots uv run mypackage config   # error, not silently ignored
```

## Attack classes: go through all of them

- [ ] **The hostile upstream**: malformed JSON, wrong types, huge values, 5xx and 429, slow responses.
- [ ] **The clock**: naive timestamps, DST transitions, `:45` offsets, far-future and far-past dates, a machine whose clock is set wrong.
- [ ] **Retry amplification**: can one bad response multiply into N×M requests? Is there a sleep after the last attempt?
- [ ] **Pagination under concurrent writes**: cursor loops, endless cursors, oversize pages, items added or removed mid-scan.
- [ ] **Filesystem and process**: paths, permissions, symlinks, signals, partial writes, running two copies at once.
- [ ] **The config surface**: zero, negative, `True`, NaN, empty string, unknown keys, env overriding CLI.

For each class, record the result in `THREAT_MODEL.md` and add a regression test to `tests/test_adversarial.py`.

## Make it repeatable

| Practice | Where it lives here |
|---|---|
| Fuzz the parsers | `tests/test_adversarial.py::test_fuzz_*` (Hypothesis) |
| Fault injection in CI | `test_fault_injection` + the `adversarial` CI job (`HYPOTHESIS_PROFILE=ci`) |
| Write the threat model down | [`THREAT_MODEL.md`](../THREAT_MODEL.md) |
| Keep a pathological fake next to the well-behaved one | `tests/fakes.py`: `PathologicalUpstream` / `WellBehavedUpstream` |
| Two rituals for code review | PR template: *attack it* and *red-team the fix, not just the bug* |

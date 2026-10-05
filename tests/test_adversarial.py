"""Adversarial review, written down so it runs on every change.

Each test answers "what does a hostile upstream, clock, or caller do to us?"
They use the pathological fake and are marked ``adversarial``, so CI can run
them on their own with the high-effort Hypothesis profile. When you fix a
bug, add its attack here as well ("red-team the fix, not just the bug").
"""

import contextlib
from datetime import UTC

import pytest
import requests
from hypothesis import given
from hypothesis import strategies as st

from mypackage.client import Client, parse_item, parse_page
from mypackage.clock import parse_timestamp
from mypackage.config import load_config
from mypackage.errors import (
    RetryExhaustedError,
    TransportSecurityError,
    UpstreamError,
)
from tests.fakes import FakeResponse, PathologicalUpstream, page

pytestmark = pytest.mark.adversarial

json_values = st.recursive(
    st.none() | st.booleans() | st.integers() | st.floats() | st.text(),
    lambda children: st.lists(children) | st.dictionaries(st.text(), children),
    max_leaves=25,
)


def make_client(session, **overrides):
    return Client(load_config({"backoff": 0.0, **overrides}), session=session)


# --- Fuzz the parsers: any input either parses or raises UpstreamError -------


@given(json_values)
def test_fuzz_parse_page(body):
    try:
        items, cursor = parse_page(body)
    except UpstreamError:
        return
    assert cursor is None or (isinstance(cursor, str) and cursor)
    assert all(item.updated_at.tzinfo is UTC for item in items)


@given(st.dictionaries(st.sampled_from(["id", "updated_at", "extra"]), json_values))
def test_fuzz_parse_item(raw):
    with contextlib.suppress(UpstreamError):
        parse_item(raw)


@given(st.text())
def test_fuzz_parse_timestamp(raw):
    with contextlib.suppress(UpstreamError):
        parse_timestamp(raw)


# --- The hostile upstream ------------------------------------------------------


def test_cursor_loop_is_detected():
    hostile = PathologicalUpstream().then(page(1, "A"), page(1, "B"), page(1, "A"))
    with pytest.raises(UpstreamError, match="loop"):
        list(make_client(hostile).iter_items())


def test_endless_fresh_cursors_are_bounded():
    counter = iter(range(10**6))

    class Endless(PathologicalUpstream):
        def get(self, url, **kwargs):
            self.calls += 1
            return FakeResponse(body=page(1, f"c{next(counter)}"))

    hostile = Endless()
    with pytest.raises(UpstreamError, match="max_pages"):
        list(make_client(hostile, max_pages=50).iter_items())
    assert hostile.calls == 50


def test_oversized_page_is_rejected():
    hostile = PathologicalUpstream().then(page(11, None))
    with pytest.raises(UpstreamError, match="more than limit"):
        list(make_client(hostile, page_size=10).iter_items())


def test_naive_timestamps_from_upstream_are_rejected():
    hostile = PathologicalUpstream().then(page(1, None, stamp="2026-01-01T00:00:00"))
    with pytest.raises(UpstreamError, match="naive"):
        list(make_client(hostile).iter_items())


@pytest.mark.parametrize(
    "body",
    [None, [], "items", {"items": None}, {"items": [], "next": ""}, {"items": [], "next": 7}],
)
def test_malformed_pages(body):
    hostile = PathologicalUpstream().then(FakeResponse(body=body))
    with pytest.raises(UpstreamError):
        list(make_client(hostile).iter_items())


# --- Fault injection: random faults never produce silent, partial, or wrong data ---

faults = st.sampled_from(
    [
        requests.exceptions.ConnectionError("reset"),
        requests.exceptions.Timeout("slow"),
        requests.exceptions.SSLError("mitm"),
        FakeResponse(status_code=500),
        FakeResponse(status_code=429),
        FakeResponse(raw_text="<html>"),
    ]
)


@given(st.lists(st.one_of(faults, st.just("ok")), min_size=1, max_size=12), st.integers(1, 4))
def test_fault_injection(script, retries):
    # Faults are interleaved with three real pages. Pages no "ok" step used are served last.
    pages = [page(2, "c1"), page(2, "c2"), page(1, None)]
    steps = [pages.pop(0) if step == "ok" and pages else step for step in script]
    steps = [s for s in steps if s != "ok"] + pages
    hostile = PathologicalUpstream().then(*steps)
    try:
        items = list(make_client(hostile, retries=retries).iter_items())
    except (UpstreamError, RetryExhaustedError, TransportSecurityError):
        # A failure must be one of these typed errors. Anything else escapes and fails the test.
        return
    # Success means every page was served: 2 + 2 + 1 items, nothing more, nothing less.
    assert len(items) == 5
    assert hostile.calls <= len(steps)

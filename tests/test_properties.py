"""Property-based tests: state what must always hold, and let Hypothesis hunt for counterexamples.

Once line and branch coverage is at 100%, adding more hand-picked examples
finds little. A property is checked against hundreds of generated inputs
(a thousand under ``HYPOTHESIS_PROFILE=ci``).
"""

from datetime import UTC, datetime, timedelta, timezone

import pytest
import requests
from hypothesis import given
from hypothesis import strategies as st

from mypackage.client import Client
from mypackage.clock import ensure_aware, from_epoch, parse_timestamp
from mypackage.config import DEFAULTS, load_config
from mypackage.errors import RetryExhaustedError
from mypackage.retry import fetch_with_retry
from tests.fakes import WellBehavedUpstream

offsets = st.integers(min_value=-14 * 60, max_value=14 * 60).map(
    lambda m: timezone(timedelta(minutes=m))
)
# Keep clear of year 1 and year 9999, where converting to UTC would overflow.
aware_datetimes = st.datetimes(
    min_value=datetime(1900, 1, 1),  # noqa: DTZ001 - Hypothesis bounds must be naive
    max_value=datetime(9000, 1, 1),  # noqa: DTZ001
    timezones=offsets,
)


@given(aware_datetimes)
def test_timestamp_round_trip_preserves_the_instant(dt):
    parsed = parse_timestamp(dt.isoformat())
    assert parsed == dt
    assert parsed.tzinfo is UTC


@given(aware_datetimes)
def test_ensure_aware_is_idempotent(dt):
    once = ensure_aware(dt)
    assert ensure_aware(once) == once


@given(st.integers(min_value=-(10**10), max_value=10**10))
def test_from_epoch_round_trips(seconds):
    assert from_epoch(seconds).timestamp() == seconds


@given(st.integers(1, 10), st.floats(0, 60, allow_nan=False))
def test_backoff_schedule(retries, backoff):
    """``retries`` attempts and ``retries - 1`` sleeps, each one twice as long as the last."""
    slept: list[float] = []
    calls: list[int] = []

    def network_down():
        calls.append(1)
        raise requests.exceptions.ConnectionError

    with pytest.raises(RetryExhaustedError):
        fetch_with_retry(network_down, retries=retries, backoff=backoff, sleep=slept.append)
    assert len(calls) == retries
    assert slept == [backoff * 2**i for i in range(retries - 1)]


@given(st.integers(0, 300), st.integers(1, 50))
def test_pagination_yields_every_item_exactly_once(total, page_size):
    client = Client(load_config({"page_size": page_size}), session=WellBehavedUpstream(total))
    ids = [item.id for item in client.iter_items()]
    assert ids == [f"item-{i}" for i in range(total)]


@given(st.integers(1, 10), st.integers(1, 1_000))
def test_load_config_never_aliases_defaults(retries, page_size):
    config = load_config({"retries": retries, "page_size": page_size})
    config["http"]["base_url"] = "https://mutated.example.com"
    assert DEFAULTS["http"]["base_url"] == "https://api.example.com"

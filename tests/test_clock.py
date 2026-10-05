from datetime import UTC, datetime, timedelta, timezone

import pytest
import time_machine

from mypackage.clock import ensure_aware, from_epoch, parse_timestamp, utc_now
from mypackage.errors import UpstreamError

KATHMANDU = timezone(timedelta(hours=5, minutes=45))


def test_utc_now_is_aware_utc():
    now = utc_now()
    assert now.utcoffset() == timedelta(0)


def test_utc_now_ignores_local_timezone():
    instant = datetime(2026, 3, 29, 1, 30, tzinfo=KATHMANDU)
    with time_machine.travel(instant, tick=False):
        assert utc_now() == instant
        assert utc_now().tzinfo is UTC


def test_parse_timestamp_normalises_to_utc():
    assert parse_timestamp("2026-01-01T05:45:00+05:45") == datetime(2026, 1, 1, tzinfo=UTC)


@pytest.mark.parametrize("raw", ["2026-01-01T00:00:00", "yesterday", "", 1_700_000_000, None])
def test_parse_timestamp_rejects_naive_and_garbage(raw):
    with pytest.raises(UpstreamError):
        parse_timestamp(raw)


def test_ensure_aware_rejects_naive():
    with pytest.raises(UpstreamError, match="naive"):
        ensure_aware(datetime(2026, 1, 1))  # noqa: DTZ001


def test_from_epoch():
    assert from_epoch(0) == datetime(1970, 1, 1, tzinfo=UTC)


@pytest.mark.parametrize("raw", [float("inf"), float("nan"), 10**20, "0", True, None])
def test_from_epoch_rejects_garbage(raw):
    with pytest.raises(UpstreamError):
        from_epoch(raw)

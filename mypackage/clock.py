"""The only module that reads the wall clock.

``datetime`` does not tell naive and aware values apart in the type system.
``AwareDatetime`` is a ``NewType``, and the only way to make one is through
this module, so the type checker can tell the two apart. See
``docs/adr/0001-aware-utc-datetimes.md``.
"""

import math
from datetime import UTC, datetime
from typing import NewType, Protocol

from mypackage.errors import UpstreamError

AwareDatetime = NewType("AwareDatetime", datetime)


class Clock(Protocol):
    """Anything that can tell the current aware UTC time. Inject it, so tests control time."""

    def __call__(self) -> AwareDatetime:
        """Return the current time."""
        ...


def utc_now() -> AwareDatetime:
    """Return the current time as an aware UTC datetime."""
    return AwareDatetime(datetime.now(UTC))


def ensure_aware(value: datetime) -> AwareDatetime:
    """Convert an aware datetime to UTC.

    Raises:
        UpstreamError: If ``value`` is naive. Guessing its timezone is how
            expiry bugs that only show up in some timezones get in.

    """
    if value.tzinfo is None or value.utcoffset() is None:
        msg = f"refusing naive datetime {value.isoformat()!r}"
        raise UpstreamError(msg)
    return AwareDatetime(value.astimezone(UTC))


def parse_timestamp(raw: object) -> AwareDatetime:
    """Parse an ISO-8601 timestamp that has an explicit offset.

    Raises:
        UpstreamError: If ``raw`` is not a string, is not ISO-8601, or has no offset.

    """
    if not isinstance(raw, str):
        msg = f"timestamp must be a string, got {type(raw).__name__}"
        raise UpstreamError(msg)
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        msg = f"not an ISO-8601 timestamp: {raw!r}"
        raise UpstreamError(msg) from exc
    return ensure_aware(parsed)


def from_epoch(seconds: object) -> AwareDatetime:
    """Convert a Unix timestamp in seconds to an aware UTC datetime.

    Raises:
        UpstreamError: If ``seconds`` is not a finite, in-range number.

    """
    if isinstance(seconds, bool) or not isinstance(seconds, int | float):
        msg = f"epoch seconds must be a number, got {type(seconds).__name__}"
        raise UpstreamError(msg)
    if not math.isfinite(seconds):
        msg = f"epoch seconds must be finite, got {seconds!r}"
        raise UpstreamError(msg)
    try:
        return AwareDatetime(datetime.fromtimestamp(seconds, tz=UTC))
    except (OverflowError, OSError, ValueError) as exc:
        msg = f"epoch seconds out of range: {seconds!r}"
        raise UpstreamError(msg) from exc

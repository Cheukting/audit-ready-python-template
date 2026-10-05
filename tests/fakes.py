"""Test doubles for the upstream API.

Keep a pathological fake next to the well-behaved one. The well-behaved fake
proves the happy path works. The pathological fake is how you find out what
happens when the upstream lies, loops, stalls, or is attacked.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

import requests


@dataclass
class FakeResponse:
    """Just enough of ``requests.Response``."""

    status_code: int = 200
    body: object = None
    raw_text: str | None = None

    def json(self) -> object:
        """Return the body, or raise like requests does if the body is not JSON."""
        if self.raw_text is not None:
            raise requests.exceptions.JSONDecodeError("Expecting value", self.raw_text, 0)
        return self.body


@dataclass
class WellBehavedUpstream:
    """Serves ``total`` items, ``limit`` at a time, with opaque cursors."""

    total: int = 25
    calls: list[dict[str, object]] = field(default_factory=list)

    def get(self, url, *, params: Mapping[str, str | int], timeout: float, verify: bool):
        """Serve one page."""
        self.calls.append(
            {"url": url, "params": dict(params), "timeout": timeout, "verify": verify}
        )
        limit = int(params["limit"])
        start = int(str(params.get("cursor", "c0"))[1:])
        end = min(start + limit, self.total)
        items = [
            {"id": f"item-{i}", "updated_at": f"2026-01-01T00:00:{i % 60:02d}+00:00"}
            for i in range(start, end)
        ]
        return FakeResponse(body={"items": items, "next": f"c{end}" if end < self.total else None})


@dataclass
class PathologicalUpstream:
    """Replays a script of responses or exceptions, one per call. The last entry repeats."""

    script: list[object] = field(default_factory=list)
    calls: int = 0

    def then(self, *steps: object) -> "PathologicalUpstream":
        """Append steps. Each step is a ``FakeResponse``, an exception, or a page body."""
        self.script.extend(steps)
        return self

    def get(self, url, *, params, timeout, verify):
        """Play the next scripted step."""
        step = self.script[min(self.calls, len(self.script) - 1)]
        self.calls += 1
        if isinstance(step, BaseException):
            raise step
        if isinstance(step, FakeResponse):
            return step
        return FakeResponse(body=step)


def page(n: int, cursor: str | None, *, stamp: str = "2026-01-01T00:00:00Z") -> dict[str, object]:
    """Build a page body with ``n`` valid items."""
    return {"items": [{"id": f"x{i}", "updated_at": stamp} for i in range(n)], "next": cursor}


def no_sleep() -> tuple[list[float], Callable[[float], None]]:
    """Return a list and a ``sleep`` replacement that records into it."""
    slept: list[float] = []
    return slept, slept.append

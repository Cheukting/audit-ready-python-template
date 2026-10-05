"""HTTP client for a paginated JSON API.

Treat the upstream as hostile. Every response is validated before use, and
pagination has an upper bound:

- Every request goes through one ``Session`` with an explicit timeout and TLS
  verification. ruff bans ``requests.get`` and ``requests.post``.
- A body that is not JSON, or JSON of the wrong shape, raises ``UpstreamError``.
- A cursor that has been seen before (a loop), or more than ``max_pages``
  pages, stops pagination with an error instead of running forever.
"""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Final, Protocol

import requests

from mypackage.clock import AwareDatetime, parse_timestamp
from mypackage.config import Config
from mypackage.errors import UpstreamError
from mypackage.retry import fetch_with_retry

MAX_ID_LENGTH: Final = 256


class Response(Protocol):
    """The parts of ``requests.Response`` we rely on."""

    @property
    def status_code(self) -> int:
        """The HTTP status code."""
        ...

    def json(self) -> object:
        """Decode the body. Raises ``ValueError`` if it is not JSON."""
        ...


class HttpSession(Protocol):
    """The parts of ``requests.Session`` we rely on, so tests can swap in a fake."""

    def get(
        self,
        url: str,
        *,
        params: Mapping[str, str | int],
        timeout: float,
        verify: bool,
    ) -> Response:
        """Send a GET request."""
        ...


@dataclass(frozen=True, slots=True)
class Item:
    """One validated record from the API."""

    id: str
    updated_at: AwareDatetime


def parse_item(raw: object) -> Item:
    """Validate one raw record and turn it into an ``Item``.

    Raises:
        UpstreamError: If the record does not have the expected shape.

    """
    if not isinstance(raw, dict):
        msg = f"item must be an object, got {type(raw).__name__}"
        raise UpstreamError(msg)
    item_id = raw.get("id")
    if not isinstance(item_id, str) or not item_id or len(item_id) > MAX_ID_LENGTH:
        msg = f"item id must be a non-empty string of at most {MAX_ID_LENGTH} chars"
        raise UpstreamError(msg)
    return Item(id=item_id, updated_at=parse_timestamp(raw.get("updated_at")))


def parse_page(body: object) -> tuple[list[Item], str | None]:
    """Validate one page body and return its items and the next cursor (or ``None``).

    Raises:
        UpstreamError: If the page does not have the expected shape.

    """
    if not isinstance(body, dict):
        msg = f"page must be an object, got {type(body).__name__}"
        raise UpstreamError(msg)
    raw_items = body.get("items")
    if not isinstance(raw_items, list):
        msg = "page 'items' must be a list"
        raise UpstreamError(msg)
    cursor = body.get("next")
    if cursor is not None and (not isinstance(cursor, str) or not cursor):
        msg = "page 'next' must be a non-empty string or null"
        raise UpstreamError(msg)
    return [parse_item(raw) for raw in raw_items], cursor


class Client:
    """A small client for the example API."""

    def __init__(self, config: Config, session: HttpSession | None = None) -> None:
        """Create a client. Pass ``session`` to inject a fake in tests."""
        self._config = config
        self._session: HttpSession = session if session is not None else requests.Session()

    def _url(self, path: str) -> str:
        # A protocol-relative or absolute path would send our request somewhere else.
        if not path.startswith("/") or path.startswith("//"):
            msg = f"path must be absolute and same-origin, got {path!r}"
            raise ValueError(msg)
        return self._config["http"]["base_url"].rstrip("/") + path

    def get_json(self, path: str, params: Mapping[str, str | int] | None = None) -> object:
        """GET ``path`` with retries and return the decoded JSON body.

        Raises:
            UpstreamError: If the status is not 200 or the body is not JSON.
            RetryExhaustedError: If every attempt failed with a network error.
            TransportSecurityError: On a TLS failure.

        """
        url = self._url(path)
        http = self._config["http"]

        def attempt() -> Response:
            return self._session.get(
                url, params=params or {}, timeout=http["timeout"], verify=http["verify_tls"]
            )

        response = fetch_with_retry(
            attempt, retries=self._config["retries"], backoff=self._config["backoff"]
        )
        if response.status_code != 200:  # noqa: PLR2004
            msg = f"GET {path} returned HTTP {response.status_code}"
            raise UpstreamError(msg)
        try:
            return response.json()
        except ValueError as exc:
            msg = f"GET {path} did not return JSON"
            raise UpstreamError(msg) from exc

    def iter_items(self, path: str = "/items") -> Iterator[Item]:
        """Yield every item, following ``next`` cursors.

        Raises:
            UpstreamError: If a page is malformed, a cursor repeats, a page is
                larger than ``page_size``, or there are more than ``max_pages`` pages.

        """
        page_size = self._config["page_size"]
        seen: set[str] = set()
        cursor: str | None = None
        for _ in range(self._config["max_pages"]):
            params: dict[str, str | int] = {"limit": page_size}
            if cursor is not None:
                params["cursor"] = cursor
            items, cursor = parse_page(self.get_json(path, params))
            if len(items) > page_size:
                msg = f"upstream returned {len(items)} items, more than limit={page_size}"
                raise UpstreamError(msg)
            yield from items
            if cursor is None:
                return
            if cursor in seen:
                msg = f"pagination loop: cursor {cursor!r} seen before"
                raise UpstreamError(msg)
            seen.add(cursor)
        msg = f"pagination exceeded max_pages={self._config['max_pages']}"
        raise UpstreamError(msg)

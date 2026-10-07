"""Retry with exponential backoff that fails loudly.

It avoids the usual mistakes in a hand-written retry loop:

- When every attempt fails it raises ``RetryExhaustedError``. It never returns
  ``None``, so a caller cannot mistake "the server was down" for "no result".
- ``requests.exceptions.SSLError`` is a subclass of ``ConnectionError``, which
  is a subclass of ``RequestException``. Here it is caught first and raised
  straight away as ``TransportSecurityError``. A failed TLS handshake is a
  security signal and must not be retried or thrown away.
- It does not sleep after the last attempt, because that only adds latency.
"""

import time
from collections.abc import Callable
from typing import Protocol, TypeVar

import requests

from mypackage.errors import RetryExhaustedError, TransportSecurityError

T_co = TypeVar("T_co", covariant=True)

# Only these are worth another attempt. Anything else is a bug or a refusal, so it is raised.
RETRYABLE: tuple[type[BaseException], ...] = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
)


class Fetch(Protocol[T_co]):
    """A zero-argument call that does the work and may raise."""

    def __call__(self) -> T_co:
        """Do one attempt."""
        ...


def fetch_with_retry(
    fetch: Fetch[T_co],
    *,
    retries: int = 3,
    backoff: float = 0.5,
    sleep: Callable[[float], None] = time.sleep,
) -> T_co:
    """Call ``fetch`` up to ``retries`` times and return its first successful result.

    Before attempt ``n`` (counting from 0) it sleeps ``backoff * 2 ** (n - 1)``
    seconds. The first attempt never waits.

    Raises:
        ValueError: If ``retries < 1`` or ``backoff < 0``.
        TransportSecurityError: On the first TLS failure, without retrying.
        RetryExhaustedError: When every attempt failed. The last error is its ``__cause__``.
        Exception: Any error that is not retryable, unchanged.

    """
    if retries < 1:
        msg = f"retries must be >= 1, got {retries}"
        raise ValueError(msg)
    if backoff < 0:
        msg = f"backoff must be >= 0, got {backoff}"
        raise ValueError(msg)

    last_error: BaseException | None = None
    for attempt in range(retries):
        if attempt:
            sleep(backoff * 2 ** (attempt - 1))
        try:
            return fetch()
        except requests.exceptions.SSLError as exc:
            msg = "TLS failure; refusing to retry"
            raise TransportSecurityError(msg) from exc
        except RETRYABLE as exc:
            last_error = exc
    raise RetryExhaustedError(retries) from last_error

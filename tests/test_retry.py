import pytest
import requests

from mypackage.errors import RetryExhaustedError, TransportSecurityError
from mypackage.retry import fetch_with_retry
from tests.fakes import no_sleep


class Flaky:
    """Fails ``failures`` times with ``error``, then returns ``"ok"``."""

    def __init__(self, failures, error=None):
        self.failures = failures
        self.error = error or requests.exceptions.ConnectionError("boom")
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if self.calls <= self.failures:
            raise self.error
        return "ok"


def test_first_success_does_not_sleep():
    slept, sleep = no_sleep()
    assert fetch_with_retry(Flaky(0), sleep=sleep) == "ok"
    assert slept == []


def test_recovers_after_transient_failures():
    slept, sleep = no_sleep()
    fetch = Flaky(2)
    assert fetch_with_retry(fetch, retries=3, backoff=0.5, sleep=sleep) == "ok"
    assert fetch.calls == 3
    assert slept == [0.5, 1.0]


def test_exhaustion_raises_instead_of_returning_none():
    slept, sleep = no_sleep()
    with pytest.raises(RetryExhaustedError) as info:
        fetch_with_retry(Flaky(99), retries=3, backoff=0.5, sleep=sleep)
    assert info.value.attempts == 3
    assert isinstance(info.value.__cause__, requests.exceptions.ConnectionError)
    # No sleep after the final attempt.
    assert slept == [0.5, 1.0]


def test_tls_failure_is_never_retried():
    slept, sleep = no_sleep()
    fetch = Flaky(99, requests.exceptions.SSLError("handshake failed"))
    with pytest.raises(TransportSecurityError):
        fetch_with_retry(fetch, retries=5, sleep=sleep)
    assert fetch.calls == 1
    assert slept == []


def test_non_retryable_errors_propagate_unchanged():
    fetch = Flaky(99, KeyError("bug"))
    with pytest.raises(KeyError):
        fetch_with_retry(fetch, retries=5, sleep=no_sleep()[1])
    assert fetch.calls == 1


@pytest.mark.parametrize(("retries", "backoff"), [(0, 0.5), (-3, 0.5), (1, -0.1)])
def test_invalid_arguments(retries, backoff):
    with pytest.raises(ValueError, match=">= "):
        fetch_with_retry(Flaky(0), retries=retries, backoff=backoff)

import pytest
import requests

from mypackage.client import Client, parse_item
from mypackage.config import load_config
from mypackage.errors import RetryExhaustedError, TransportSecurityError, UpstreamError
from tests.fakes import FakeResponse, page

FAST = {"backoff": 0.0}


def make_client(session, **overrides):
    return Client(load_config({**FAST, **overrides}), session=session)


def test_default_session_is_a_requests_session():
    assert isinstance(Client(load_config())._session, requests.Session)


def test_iter_items_follows_cursors(upstream):
    items = list(make_client(upstream, page_size=10).iter_items())
    assert [i.id for i in items] == [f"item-{n}" for n in range(25)]
    assert len(upstream.calls) == 3
    assert all(call["verify"] is True for call in upstream.calls)
    assert all(call["timeout"] == 10.0 for call in upstream.calls)


def test_empty_listing(hostile):
    hostile.then(page(0, None))
    assert list(make_client(hostile).iter_items()) == []


@pytest.mark.parametrize("path", ["items", "//evil.example.com/x", "https://evil.example.com/"])
def test_rejects_paths_that_change_origin(path, upstream):
    with pytest.raises(ValueError, match="same-origin"):
        make_client(upstream).get_json(path)


def test_non_200_is_an_error(hostile):
    hostile.then(FakeResponse(status_code=503))
    with pytest.raises(UpstreamError, match="503"):
        make_client(hostile).get_json("/items")


def test_non_json_body_is_an_error(hostile):
    hostile.then(FakeResponse(raw_text="<html>maintenance</html>"))
    with pytest.raises(UpstreamError, match="JSON"):
        make_client(hostile).get_json("/items")


def test_network_errors_are_retried_then_surface(hostile):
    hostile.then(requests.exceptions.ConnectionError("down"))
    with pytest.raises(RetryExhaustedError):
        make_client(hostile, retries=3).get_json("/items")
    assert hostile.calls == 3


def test_tls_failure_surfaces_immediately(hostile):
    hostile.then(requests.exceptions.SSLError("bad cert"))
    with pytest.raises(TransportSecurityError):
        make_client(hostile, retries=3).get_json("/items")
    assert hostile.calls == 1


def test_parse_item_rejects_overlong_id():
    with pytest.raises(UpstreamError, match="id"):
        parse_item({"id": "x" * 257, "updated_at": "2026-01-01T00:00:00Z"})


@pytest.mark.parametrize("raw", [None, [], "item-1"])
def test_parse_item_rejects_non_objects(raw):
    with pytest.raises(UpstreamError, match="object"):
        parse_item(raw)

import pytest

from mypackage.config import DEFAULTS, from_env, load_config
from mypackage.errors import ConfigError


def test_defaults_are_valid():
    assert load_config() == DEFAULTS


def test_load_config_is_a_deep_copy():
    config = load_config()
    config["http"]["timeout"] = 1.0
    assert DEFAULTS["http"]["timeout"] == 10.0
    assert load_config()["http"]["timeout"] == 10.0


def test_nested_override_keeps_siblings():
    config = load_config({"http": {"timeout": 2.5}})
    assert config["http"]["timeout"] == 2.5
    assert config["http"]["verify_tls"] is True


@pytest.mark.parametrize(
    "overrides",
    [
        {"retries": 0},
        {"retries": -3},
        {"retries": True},
        {"retries": "3"},
        {"page_size": 0},
        {"max_pages": 10**9},
        {"backoff": -1},
        {"backoff": float("nan")},
        {"backoff": "fast"},
        {"http": {"timeout": 0}},
        {"http": {"verify_tls": "no"}},
        {"http": {"base_url": "http://plaintext.example.com"}},
        {"http": {"base_url": 42}},
        {"http": "not-a-mapping"},
        {"unknown": 1},
        {"http": {"unknown": 1}},
    ],
)
def test_invalid_overrides_are_rejected(overrides):
    with pytest.raises(ConfigError):
        load_config(overrides)


def test_environment_overrides(monkeypatch):
    monkeypatch.setenv("MYPACKAGE_RETRIES", "5")
    assert load_config()["retries"] == 5


def test_explicit_overrides_beat_environment(monkeypatch):
    monkeypatch.setenv("MYPACKAGE_RETRIES", "5")
    assert load_config({"retries": 2})["retries"] == 2


@pytest.mark.parametrize("raw", ["", "three", "1.5", " "])
def test_unparsable_environment_is_an_error(raw):
    with pytest.raises(ConfigError, match="MYPACKAGE_RETRIES"):
        from_env({"MYPACKAGE_RETRIES": raw})


def test_out_of_range_environment_is_an_error(monkeypatch):
    monkeypatch.setenv("MYPACKAGE_PAGE_SIZE", "0")
    with pytest.raises(ConfigError, match="page_size"):
        load_config()

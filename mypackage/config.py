"""Typed configuration with immutable defaults.

The rules this module follows:

- The config shape is a ``TypedDict``, so the type checker sees typos and wrong types.
- ``DEFAULTS`` is ``Final`` and is never handed out directly. ``load_config``
  returns a deep copy, so changing one config cannot alias the defaults.
  ``dict(DEFAULTS)`` is a shallow copy, and semgrep blocks it.
- Every value is validated at the boundary. ``retries=-3`` or ``page_size=0``
  is rejected here instead of misbehaving three layers down.
"""

import copy
import os
from collections.abc import Mapping
from typing import Final, TypedDict, cast

from mypackage.errors import ConfigError


class HttpConfig(TypedDict):
    """Settings for talking to the upstream service."""

    base_url: str
    timeout: float
    verify_tls: bool


class Config(TypedDict):
    """The whole configuration."""

    retries: int
    backoff: float
    page_size: int
    max_pages: int
    http: HttpConfig


DEFAULTS: Final[Config] = {
    "retries": 3,
    "backoff": 0.5,
    "page_size": 100,
    "max_pages": 1_000,
    "http": {
        "base_url": "https://api.example.com",
        "timeout": 10.0,
        "verify_tls": True,
    },
}

ENV_PREFIX: Final = "MYPACKAGE_"

# Inclusive bounds. Anything outside them is a mistake or an attack, not a preference.
_INT_BOUNDS: Final[Mapping[str, tuple[int, int]]] = {
    "retries": (1, 10),
    "page_size": (1, 1_000),
    "max_pages": (1, 100_000),
}
_FLOAT_BOUNDS: Final[Mapping[str, tuple[float, float]]] = {
    "backoff": (0.0, 60.0),
    "timeout": (0.1, 300.0),
}


def _merge(base: dict[str, object], overrides: Mapping[str, object], path: str = "") -> None:
    """Recursively merge ``overrides`` into ``base`` in place, rejecting unknown keys."""
    for key, value in overrides.items():
        dotted = f"{path}{key}"
        if key not in base:
            msg = f"unknown config key: {dotted!r}"
            raise ConfigError(msg)
        current = base[key]
        if isinstance(current, dict):
            if not isinstance(value, Mapping):
                msg = f"{dotted!r} must be a mapping, got {type(value).__name__}"
                raise ConfigError(msg)
            _merge(cast("dict[str, object]", current), value, f"{dotted}.")
        else:
            base[key] = value


def _check_int(name: str, value: object) -> None:
    # bool is a subclass of int, and ``retries=True`` is never what anyone meant.
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{name!r} must be an int, got {type(value).__name__}"
        raise ConfigError(msg)
    low, high = _INT_BOUNDS[name]
    if not low <= value <= high:
        msg = f"{name!r} must be between {low} and {high}, got {value}"
        raise ConfigError(msg)


def _check_float(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = f"{name!r} must be a number, got {type(value).__name__}"
        raise ConfigError(msg)
    low, high = _FLOAT_BOUNDS[name]
    # The negated comparison also rejects NaN.
    if not low <= value <= high:
        msg = f"{name!r} must be between {low} and {high}, got {value}"
        raise ConfigError(msg)


def validate(config: Config) -> Config:
    """Return ``config`` unchanged if every value is in range.

    Raises:
        ConfigError: If any value has the wrong type or is out of range.

    """
    _check_int("retries", config["retries"])
    _check_int("page_size", config["page_size"])
    _check_int("max_pages", config["max_pages"])
    _check_float("backoff", config["backoff"])
    # Overrides are untyped, so read the values as ``object`` and do not trust the TypedDict.
    http: Mapping[str, object] = config["http"]
    _check_float("timeout", http["timeout"])
    if not isinstance(http["verify_tls"], bool):
        msg = "'http.verify_tls' must be a bool"
        raise ConfigError(msg)
    base_url = http["base_url"]
    if not isinstance(base_url, str) or not base_url.startswith("https://"):
        msg = "'http.base_url' must be an https:// URL"
        raise ConfigError(msg)
    return config


def from_env(environ: Mapping[str, str]) -> dict[str, object]:
    """Build overrides from ``MYPACKAGE_*`` environment variables.

    Only the top-level numeric settings can be set this way. Values are parsed
    strictly, and an unparsable value is an error, never silently ignored.

    Raises:
        ConfigError: If a variable is set but cannot be parsed.

    """
    overrides: dict[str, object] = {}
    for name in ("retries", "page_size", "max_pages"):
        raw = environ.get(f"{ENV_PREFIX}{name.upper()}")
        if raw is not None:
            try:
                overrides[name] = int(raw)
            except ValueError as exc:
                msg = f"{ENV_PREFIX}{name.upper()}={raw!r} is not an integer"
                raise ConfigError(msg) from exc
    return overrides


def load_config(overrides: Mapping[str, object] | None = None) -> Config:
    """Return a fresh, validated config: defaults, then environment, then ``overrides``.

    The result is a deep copy. Changing it never affects ``DEFAULTS`` or any
    other config.

    Raises:
        ConfigError: If an override names an unknown key or a value is invalid.

    """
    merged = copy.deepcopy(cast("dict[str, object]", DEFAULTS))
    _merge(merged, from_env(os.environ))
    if overrides:
        _merge(merged, overrides)
    return validate(cast("Config", merged))

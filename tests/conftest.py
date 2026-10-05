"""Fixtures and Hypothesis profiles shared across the suite."""

import os

import pytest
from hypothesis import HealthCheck, settings

from tests.fakes import PathologicalUpstream, WellBehavedUpstream

settings.register_profile("dev", max_examples=50)
settings.register_profile(
    "ci",
    max_examples=1000,
    deadline=None,  # network fakes, sleeps
    suppress_health_check=[HealthCheck.too_slow],
    derandomize=False,  # let CI find new failures
)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Keep a developer's own ``MYPACKAGE_*`` variables out of the suite."""
    for name in list(os.environ):
        if name.startswith("MYPACKAGE_"):
            monkeypatch.delenv(name)


@pytest.fixture
def upstream():
    """A well-behaved fake API with three pages of items."""
    return WellBehavedUpstream(total=25)


@pytest.fixture
def hostile():
    """A fake API that misbehaves in whichever way the test chooses."""
    return PathologicalUpstream()

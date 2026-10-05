"""Exception hierarchy.

This module is a leaf: import-linter forbids it from importing anything else
in the package (see ``.importlinter``).
"""


class MyPackageError(Exception):
    """Base class for every error this package raises on purpose."""


class ConfigError(MyPackageError, ValueError):
    """A configuration value is missing, has the wrong type, or is out of range."""


class TransportSecurityError(MyPackageError):
    """TLS failed. This is a security signal, never a transient blip, so it is never retried."""


class RetryExhaustedError(MyPackageError):
    """Every attempt failed. The last underlying error is chained as ``__cause__``."""

    def __init__(self, attempts: int) -> None:
        """Record how many attempts were made."""
        super().__init__(f"gave up after {attempts} attempt(s)")
        self.attempts = attempts


class UpstreamError(MyPackageError):
    """The upstream service answered, but with something we refuse to trust."""

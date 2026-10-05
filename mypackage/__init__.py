"""mypackage: a template package wired up for auditing AI-generated code.

Replace this package with your own code. The modules here are a small,
working example that shows the conventions the tooling enforces:

- ``errors``: the exception hierarchy. It is a leaf and imports nothing.
- ``config``: typed, immutable defaults, plus validated overrides.
- ``clock``: the only place that reads the wall clock. Everything is aware UTC.
- ``retry``: retries that fail loudly and never retry a TLS failure.
- ``client``: an HTTP client on a module-level ``Session``, with guarded pagination.
- ``cli``: the command-line entry point. It sits on the top layer.
"""

__version__ = "0.1.0"

"""Command-line entry point. This is the top layer: nothing else in the package imports it.

``argparse`` checks every number on the way in. ``--retries -3`` and
``--page-size 0`` are rejected with a usage error before any code runs.
"""

import argparse
import json
import sys
from collections.abc import Sequence
from typing import TextIO

from mypackage import __version__
from mypackage.client import Client
from mypackage.clock import parse_timestamp
from mypackage.config import load_config
from mypackage.errors import MyPackageError

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2


def positive_int(raw: str) -> int:
    """Argparse type: an integer >= 1."""
    try:
        value = int(raw)
    except ValueError as exc:
        msg = f"{raw!r} is not an integer"
        raise argparse.ArgumentTypeError(msg) from exc
    if value < 1:
        msg = f"must be >= 1, got {value}"
        raise argparse.ArgumentTypeError(msg)
    return value


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(prog="mypackage", description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--retries", type=positive_int, help="attempts per request")
    sub = parser.add_subparsers(dest="command", required=True)

    items = sub.add_parser("items", help="list every item")
    items.add_argument("--page-size", type=positive_int, help="items per page")

    sub.add_parser("config", help="print the effective configuration as JSON")

    ts = sub.add_parser("timestamp", help="validate an ISO-8601 timestamp and print it in UTC")
    ts.add_argument("value")
    return parser


def main(argv: Sequence[str] | None = None, *, out: TextIO | None = None) -> int:
    """Run the CLI and return a process exit code."""
    out = out if out is not None else sys.stdout
    args = build_parser().parse_args(argv)

    overrides: dict[str, object] = {}
    if args.retries is not None:
        overrides["retries"] = args.retries
    if getattr(args, "page_size", None) is not None:
        overrides["page_size"] = args.page_size

    try:
        config = load_config(overrides)
        if args.command == "config":
            json.dump(config, out, indent=2, sort_keys=True)
            out.write("\n")
        elif args.command == "timestamp":
            out.write(parse_timestamp(args.value).isoformat() + "\n")
        else:
            for item in Client(config).iter_items():
                out.write(f"{item.id}\t{item.updated_at.isoformat()}\n")
    except (MyPackageError, ValueError) as exc:
        # Exit non-zero so that a failure never looks like success to the caller.
        print(f"mypackage: error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    return EXIT_OK

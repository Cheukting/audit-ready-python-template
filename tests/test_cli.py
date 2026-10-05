import io
import json
import runpy

import pytest

import mypackage.client
from mypackage import __version__
from mypackage.cli import main
from tests.fakes import WellBehavedUpstream


def run(*argv):
    out = io.StringIO()
    code = main(list(argv), out=out)
    return code, out.getvalue()


def test_config_command_prints_effective_config():
    code, out = run("--retries", "2", "config")
    assert code == 0
    assert json.loads(out)["retries"] == 2


def test_timestamp_command():
    assert run("timestamp", "2026-01-01T05:45:00+05:45") == (0, "2026-01-01T00:00:00+00:00\n")


def test_timestamp_command_rejects_naive(capsys):
    code, out = run("timestamp", "2026-01-01T00:00:00")
    assert (code, out) == (1, "")
    assert "naive" in capsys.readouterr().err


def test_items_command(monkeypatch):
    monkeypatch.setattr(mypackage.client.requests, "Session", lambda: WellBehavedUpstream(3))
    code, out = run("items", "--page-size", "2")
    assert code == 0
    assert out.splitlines()[0] == "item-0\t2026-01-01T00:00:00+00:00"
    assert len(out.splitlines()) == 3


def test_bad_environment_is_reported_not_raised(monkeypatch, capsys):
    monkeypatch.setenv("MYPACKAGE_RETRIES", "lots")
    assert run("config") == (1, "")
    assert "MYPACKAGE_RETRIES" in capsys.readouterr().err


@pytest.mark.parametrize(
    "argv",
    [
        ["--retries", "0", "config"],
        ["--retries", "-3", "config"],
        ["--retries", "three", "config"],
        ["items", "--page-size", "0"],
        ["no-such-command"],
        [],
    ],
)
def test_usage_errors_exit_2(argv, capsys):
    with pytest.raises(SystemExit) as info:
        main(argv)
    assert info.value.code == 2
    assert capsys.readouterr().err


def test_version(capsys):
    with pytest.raises(SystemExit):
        main(["--version"])
    assert __version__ in capsys.readouterr().out


def test_python_dash_m(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["mypackage", "timestamp", "2026-01-01T00:00:00Z"])
    with pytest.raises(SystemExit) as info:
        runpy.run_module("mypackage", run_name="__main__")
    assert info.value.code == 0
    assert capsys.readouterr().out == "2026-01-01T00:00:00+00:00\n"

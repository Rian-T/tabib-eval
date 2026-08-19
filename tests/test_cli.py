"""The console script: it dispatches, and it owns no argument logic of its own."""

from __future__ import annotations

from tabib import cli, runs


def test_no_command_prints_the_usage(capsys):
    assert cli.main([]) == 0
    assert "tabib view" in capsys.readouterr().out


def test_an_unknown_command_is_an_error(capsys):
    assert cli.main(["nope"]) == 2


def test_run_walks_a_package_end_to_end(tmp_path, monkeypatch):
    """The whole `tabib run` path, on the scripted backend.

    It was uncovered once and broke in real use: the `run` verb shadowed the
    module of the same name inside the package, which no unit test could see
    because none of them went through the script.
    """
    monkeypatch.setattr(runs, "ROOT", tmp_path)
    assert cli.main(["run", "companion-world", "--agent", "mock",
                     "--cells", "mixed", "--n", "1", "--name", "cli"]) == 0
    assert list((tmp_path / "cli" / "companion").glob("*.eval"))


def test_the_readers_are_reached_through_their_own_module(capsys):
    # each prints its own usage and returns 2 on no argument, which is the
    # proof that the script did not re-implement their parsing
    assert cli.main(["gate"]) == 2
    assert cli.main(["report"]) == 2
    out = capsys.readouterr().out
    assert "usage: gate" in out and "usage: report" in out

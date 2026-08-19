"""The façade: what a package offers, what it refuses, and what compare reads."""

from __future__ import annotations

import pytest

import tabib
from tabib import api
from tabib.hub import cache_path, fetch
from tabib.worlds import WorldError, resolve


def test_load_gives_the_protocol_the_package_declares():
    package = tabib.load("companion-world")
    assert package.name == "companion-world"
    assert package.protocol.cells == package.scenario.cells
    assert "refusal_spills" in package.protocol.contrasts
    # the floor is a cell served twice, and the package declares one
    assert "differs_from_its_twin" in package.noise_floor
    # the controls ship with the package: blind policies plus the oracle
    assert "oracle" in package.controls and "silent" in package.controls


def test_load_refuses_a_world_that_declares_no_scenario(tmp_path):
    at = tmp_path / "bare-world"
    at.mkdir()
    (at / "manifest.toml").write_text(
        '[world]\nname = "bare-world"\nversion = "1.0.0"\n', encoding="utf-8")
    (at / "world.py").write_text("", encoding="utf-8")
    with pytest.raises(WorldError, match="declares no scenario"):
        tabib.load(str(at))


SELF_CONTAINED = '''
from tabib import Act, Measurand, Scenario, World, register

SCENARIO = register(Scenario(
    name="toy_package",
    acts=(Act("send"),),
    system="Tu traites des dossiers.",
    rows=lambda **kw: [{"id": "p1", "hi": "x", "lo": "y"}],
    build=lambda cell, row: World(prompt=row[cell], tools=[]),
    measurands=(Measurand("effect", lambda r: 1.0, ("hi", "lo")),
                Measurand("floor", lambda r: 1.0, ("hi_twin", "hi"),
                          oracle_moves="none"),),
    oracle=lambda messages, tools, tool_choice, config: None,
))
'''


def test_one_directory_can_carry_the_world_and_its_science(tmp_path):
    """The unified package: the manifest points at a scenario beside it."""
    at = tmp_path / "toy-world"
    at.mkdir()
    (at / "manifest.toml").write_text(
        '[world]\nname = "toy-world"\nversion = "1.0.0"\n'
        'scenario = "scenario.py"\n', encoding="utf-8")
    (at / "world.py").write_text("", encoding="utf-8")
    (at / "scenario.py").write_text(SELF_CONTAINED, encoding="utf-8")

    package = tabib.load(str(at))
    assert package.protocol.cells == ("hi", "lo", "hi_twin")
    assert package.noise_floor == ("floor",)


def test_run_refuses_a_cell_outside_the_protocol():
    package = tabib.load("companion-world")
    with pytest.raises(ValueError, match="does not declare"):
        tabib.run(agent="dev", world=package, cells=("whatever",))


def test_resolution_falls_back_to_the_cache(tmp_path, monkeypatch):
    monkeypatch.setattr("tabib.hub.CACHE", tmp_path)
    (tmp_path / "acme" / "companion-v1").mkdir(parents=True)
    assert resolve("acme/companion-v1") == tmp_path / "acme" / "companion-v1"
    # a name that is in worlds/ is served from there, cache or no cache
    assert resolve("acme/companion-world").name == "companion-world"
    assert resolve("acme/companion-world").parent.name == "worlds"


def test_fetch_is_never_a_download_at_load(tmp_path, monkeypatch):
    monkeypatch.setattr("tabib.hub.CACHE", tmp_path)
    assert cache_path("acme/x") == tmp_path / "acme" / "x"
    with pytest.raises(NotImplementedError):
        fetch("acme/x")


class _Fake:
    """A package-shaped stand-in over two measurands and synthetic records."""

    def __init__(self, measurands, carries=()):
        from types import SimpleNamespace
        self.name = "fake"
        self.scenario = SimpleNamespace(measurands=measurands, carries=carries,
                                        name="fake")
        self.noise_floor = ("floor",)


def _rows(cell_a, cell_b, values_a, values_b):
    return ([{"cluster": f"c{i}", "epoch": 1, "model": "m", "cell": cell_a,
              "y": v} for i, v in enumerate(values_a)]
            + [{"cluster": f"c{i}", "epoch": 1, "model": "m", "cell": cell_b,
                "y": v} for i, v in enumerate(values_b)])


def test_compare_reads_a_contrast_against_its_floor(monkeypatch):
    from tabib import Measurand

    y = lambda r: r["y"]
    effect = Measurand("effect", y, ("hi", "lo"))
    floor = Measurand("floor", y, ("hi_twin", "hi"), oracle_moves="none")
    package = _Fake((effect, floor))
    rows = (_rows("hi", "lo", [1.0] * 8, [0.0] * 8)
            + _rows("hi_twin", "hi", [1.0] * 8, [1.0] * 8))
    monkeypatch.setattr(api, "_rows", lambda result: rows)

    lines = {x["measurand"]: x for x in
             api.compare({"package": package, "scenario": "fake",
                          "log_dir": "unused"})}
    assert lines["effect"]["point"] == pytest.approx(1.0)
    assert lines["effect"]["floor"] == pytest.approx(0.0)
    assert lines["effect"]["beyond_floor"] is True
    # a floor is reported as a number of its own and nothing is read against
    # it: there is no floor under the floor
    assert lines["floor"]["point"] == pytest.approx(0.0)
    assert lines["floor"]["beyond_floor"] is None


def test_compare_against_a_baseline_is_paired(monkeypatch):
    from tabib import Measurand

    y = lambda r: r["y"]
    package = _Fake((Measurand("effect", y, ("hi", "lo")),))
    now = _rows("hi", "lo", [1.0] * 6, [0.0] * 6)
    before = _rows("hi", "lo", [0.6] * 6, [0.0] * 6)
    monkeypatch.setattr(api, "_rows", lambda result: result["rows"])

    lines = api.compare({"package": package, "scenario": "fake", "rows": now},
                        baseline={"package": package, "scenario": "fake",
                                  "name": "old", "rows": before})
    assert lines[0]["point"] == pytest.approx(0.4)
    assert lines[0]["paired_against"] == "old"

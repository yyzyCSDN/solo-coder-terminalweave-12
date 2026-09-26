from __future__ import annotations

import importlib
import json
import pkgutil

import terminalweave
from terminalweave.cli import main


def test_public_package_exports_are_importable():
    assert terminalweave.__all__ == ["TerminalScenario", "utc_now"]
    assert terminalweave.TerminalScenario is not None
    assert callable(terminalweave.utc_now)


def test_cli_demo_returns_success(capsys):
    assert main(["demo"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "clearance_m": 2.25,
        "project": "TerminalWeave",
        "safe": True,
        "tide_height_m": 1.75,
    }


def test_all_shipped_modules_import():
    modules = sorted(
        item.name
        for item in pkgutil.walk_packages(
            terminalweave.__path__, terminalweave.__name__ + "."
        )
    )
    assert len(modules) >= 120
    for module in modules:
        importlib.import_module(module)

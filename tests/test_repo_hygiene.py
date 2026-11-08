"""Fail if anything that could hold betting data or credentials is committed.

The repository is public. The pre-commit hook strips notebook outputs, but it only
runs where someone installed it, so CI runs these checks on every push and PR.
"""

from __future__ import annotations

import fnmatch
import json
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

# Tracked files matching these are refused; ALLOWED re-admits deliberate exceptions.
FORBIDDEN = [
    "*.csv",
    "*.xlsx",
    "*.xls",
    "*.json",
    "*.env",
    ".env",
    ".secrets/*",
    "*.tmp",
]
ALLOWED = [
    "samples/*.csv",
    "tests/fixtures/*",
    "scripts/appsscript.json",
    ".clasp.json",
]


def _tracked_files() -> list[str]:
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z"], cwd=REPO, check=True, capture_output=True
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("not a git checkout")
    return [p for p in out.decode().split("\0") if p]


def _matches(path: str, patterns: list[str]) -> bool:
    name = path.rsplit("/", 1)[-1]
    return any(fnmatch.fnmatch(path, p) or fnmatch.fnmatch(name, p) for p in patterns)


def test_no_data_or_credential_files_are_tracked():
    bad = [
        p
        for p in _tracked_files()
        if _matches(p, FORBIDDEN) and not _matches(p, ALLOWED)
    ]
    assert bad == [], (
        f"remove these from git (they may hold betting data or keys): {bad}"
    )


def test_no_tracked_notebook_has_outputs_or_colab_metadata():
    dirty = []
    for path in (p for p in _tracked_files() if p.endswith(".ipynb")):
        nb = json.loads((REPO / path).read_text(encoding="utf-8"))
        for i, cell in enumerate(nb.get("cells", [])):
            if cell.get("outputs") or cell.get("execution_count") is not None:
                dirty.append(f"{path} cell {i}: outputs")
            if "colab" in cell.get("metadata", {}) or "outputId" in cell.get(
                "metadata", {}
            ):
                dirty.append(f"{path} cell {i}: colab metadata")
        if "colab" in nb.get("metadata", {}):
            dirty.append(f"{path}: colab metadata")
    assert dirty == [], f"run nbstripout (pre-commit install): {dirty}"


def test_forbidden_patterns_catch_real_shapes():
    assert _matches("data/BettingPandL_2025-11-08.csv", FORBIDDEN)
    assert _matches("service_account.json", FORBIDDEN)
    assert _matches("notes/Betfair_Master.xlsx", FORBIDDEN)
    assert _matches("samples/example.csv", ALLOWED)
    assert not _matches("dashboard_lib.py", FORBIDDEN)

"""The repository refuses betting data, credentials and notebook outputs (see repo_hygiene.py)."""

from __future__ import annotations

import json
import os
import subprocess

import pytest

import repo_hygiene
from repo_hygiene import forbidden_reason, notebook_problems


def _git_or_skip() -> None:
    """Skip outside a git checkout locally, but never in CI: a skip there would quietly
    switch the guard off."""
    try:
        subprocess.run(
            ["git", "rev-parse"], cwd=repo_hygiene.REPO, check=True, capture_output=True
        )
    except (OSError, subprocess.CalledProcessError):
        if os.environ.get("CI"):
            pytest.fail("git is unavailable in CI, so the hygiene guard cannot run")
        pytest.skip("not a git checkout")


def test_this_repository_is_clean():
    _git_or_skip()
    assert repo_hygiene.tracked_tree_problems() == []


# --- what is refused ------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "data/BettingPandL_2025-11-08.csv",
        "Betfair_Master.CSV",  # upper-case extensions from Windows / Excel
        "notes/Results.XLSX",
        "exports/master.parquet",
        "backup/master.zip",
        "service_account.json",
        "keys/sa.p12",
        "Key.JSON",
        ".env",
        ".env.local",
        "prod.env",
        ".envrc",  # direnv
        ".env-local",
        "config/.env_prod",
        ".secrets/anything.txt",
        "sub/.secrets/key",
        "data/Betfair_Master.csv.tmp",
        "samples/nested/deep.csv",  # the samples exception is one level only
        "tests/fixtures/real/BettingPandL.xlsx",  # fixtures admit JSON only
        "tests/fixtures/export.csv",
        "out/last_run.html",  # nbconvert export of a run
        "report.PDF",
        ".secrets/.clasp.json",  # .clasp.json is allowed at the root only
    ],
)
def test_refused(path):
    assert forbidden_reason(path) is not None


@pytest.mark.parametrize(
    "path",
    [
        "dashboard_lib.py",
        "notebooks/betfair_dashboard_STABLE.ipynb",
        "scripts/dashboard_charts.gs",
        ".env.example",
        "samples/example.csv",
        "tests/fixtures/sheet_response.json",
        "scripts/appsscript.json",
        ".clasp.json",
        "README.md",
    ],
)
def test_allowed(path):
    assert forbidden_reason(path) is None


# --- notebooks ------------------------------------------------------------


def _nb(cells: list[dict], metadata: dict | None = None) -> str:
    return json.dumps({"cells": cells, "metadata": metadata or {}})


CLEAN_CODE = {
    "cell_type": "code",
    "metadata": {},
    "outputs": [],
    "execution_count": None,
    "source": [],
}


def test_clean_notebook_passes():
    assert notebook_problems(_nb([CLEAN_CODE]), "nb") == []


@pytest.mark.parametrize(
    "cell",
    [
        {**CLEAN_CODE, "outputs": [{"output_type": "stream", "text": ["529.21"]}]},
        {**CLEAN_CODE, "execution_count": 3},
        {**CLEAN_CODE, "metadata": {"colab": {}}},
        {**CLEAN_CODE, "metadata": {"outputId": "x"}},
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [],
            "attachments": {"a.png": {"image/png": "iVBOR"}},
        },
    ],
)
def test_dirty_cells_are_reported(cell):
    assert notebook_problems(_nb([cell]), "nb")


def test_notebook_level_colab_metadata_is_reported():
    assert notebook_problems(
        _nb([CLEAN_CODE], {"colab": {"mount_file_id": "1tb"}}), "nb"
    )


# --- every commit in a push or PR -----------------------------------------


@pytest.fixture
def scratch_repo(tmp_path, monkeypatch):
    """A throwaway git repo that repo_hygiene treats as the repository."""

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=tmp_path, check=True, capture_output=True, text=True
        ).stdout.strip()

    try:
        git("init", "-q", "-b", "main")
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("git unavailable")
    git("config", "user.email", "test@example.invalid")
    git("config", "user.name", "test")
    git("config", "commit.gpgsign", "false")
    (tmp_path / "README.md").write_text("x\n")
    git("add", ".")
    git("commit", "-q", "-m", "base")
    monkeypatch.setattr(repo_hygiene, "REPO", tmp_path)
    return tmp_path, git


def test_range_catches_data_added_then_deleted(scratch_repo):
    root, git = scratch_repo
    base = git("rev-parse", "HEAD")
    (root / "Betfair_Master.csv").write_text("Market,Settled date,Profit_Loss\n")
    git("add", ".")
    git("commit", "-q", "-m", "oops")
    git("rm", "-q", "Betfair_Master.csv")
    git("commit", "-q", "-m", "remove it")

    assert repo_hygiene.tracked_tree_problems() == []  # the final tree looks clean
    problems = repo_hygiene.range_problems(f"{base}..HEAD")
    assert len(problems) == 1 and "Betfair_Master.csv" in problems[0]


def test_range_catches_a_notebook_committed_with_outputs_then_stripped(scratch_repo):
    root, git = scratch_repo
    base = git("rev-parse", "HEAD")
    dirty = {**CLEAN_CODE, "outputs": [{"output_type": "stream", "text": ["529.21"]}]}
    (root / "nb.ipynb").write_text(_nb([dirty]))
    git("add", ".")
    git("commit", "-q", "-m", "with outputs")
    (root / "nb.ipynb").write_text(_nb([CLEAN_CODE]))
    git("commit", "-q", "-am", "stripped")

    problems = repo_hygiene.range_problems(f"{base}..HEAD")
    assert len(problems) == 1 and "outputs" in problems[0]


def test_range_with_all_zero_base_checks_only_the_pushed_commit(scratch_repo):
    root, git = scratch_repo
    # Old history with data must not be re-reported on a first push.
    (root / "old.csv").write_text("a\n")
    git("add", ".")
    git("commit", "-q", "-m", "old data")
    git("rm", "-q", "old.csv")
    git("commit", "-q", "-m", "clean")
    assert repo_hygiene.range_problems(f"{'0' * 40}..HEAD") == []


def test_cli_exit_codes(scratch_repo, capsys):
    root, git = scratch_repo
    base = git("rev-parse", "HEAD")
    assert repo_hygiene.main(["--range", f"{base}..HEAD"]) == 0
    (root / "key.json").write_text("{}")
    git("add", ".")
    git("commit", "-q", "-m", "key")
    assert repo_hygiene.main(["--range", f"{base}..HEAD"]) == 1
    assert "key.json" in capsys.readouterr().out


def test_range_catches_a_file_added_only_in_a_merge_commit(scratch_repo):
    root, git = scratch_repo
    base = git("rev-parse", "HEAD")
    git("switch", "-q", "-c", "side")
    (root / "side.md").write_text("side\n")
    git("add", ".")
    git("commit", "-q", "-m", "side")
    git("switch", "-q", "main")
    (root / "main.md").write_text("main\n")
    git("add", ".")
    git("commit", "-q", "-m", "main")
    git("merge", "-q", "--no-ff", "--no-commit", "side")
    (root / "Betfair_Master.csv").write_text("Market\n")  # staged while merging
    git("add", ".")
    git("commit", "-q", "-m", "merge side")
    git("rm", "-q", "Betfair_Master.csv")
    git("commit", "-q", "-m", "remove it")

    problems = repo_hygiene.range_problems(f"{base}..HEAD")
    assert len(problems) == 1 and "Betfair_Master.csv" in problems[0]


def test_ordinary_merge_is_not_reported(scratch_repo):
    root, git = scratch_repo
    base = git("rev-parse", "HEAD")
    git("switch", "-q", "-c", "side")
    (root / "side.md").write_text("side\n")
    git("add", ".")
    git("commit", "-q", "-m", "side")
    git("switch", "-q", "main")
    git("merge", "-q", "--no-ff", "-m", "merge", "side")
    assert repo_hygiene.range_problems(f"{base}..HEAD") == []


@pytest.mark.parametrize("spec", ["..HEAD", "HEAD..", "HEAD"])
def test_range_without_both_ends_is_refused(scratch_repo, spec):
    with pytest.raises(ValueError):
        repo_hygiene.range_problems(spec)


def test_unknown_base_commit_fails_with_a_plain_message(scratch_repo, capsys):
    assert repo_hygiene.main(["--range", f"{'1' * 40}..HEAD"]) == 1
    assert "could not read the commits" in capsys.readouterr().out

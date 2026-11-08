"""Checks on the committed notebook itself, and an end-to-end run of Steps 0–7."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest
import pytz

REPO = Path(__file__).resolve().parent.parent
NOTEBOOK = REPO / "notebooks" / "betfair_dashboard_STABLE.ipynb"


def _notebook() -> dict:
    return json.loads(NOTEBOOK.read_text(encoding="utf-8"))


def test_committed_notebook_has_no_outputs():
    # Outputs have held real betting results, and the repository is public.
    dirty = [
        i
        for i, cell in enumerate(_notebook()["cells"])
        if cell["cell_type"] == "code"
        and (cell.get("outputs") or cell.get("execution_count") is not None)
    ]
    assert dirty == [], (
        f"cells {dirty} have outputs; run nbstripout (pre-commit install)"
    )


def test_committed_notebook_has_no_colab_metadata():
    nb = _notebook()
    assert "colab" not in nb["metadata"]  # held the Drive mount_file_id
    assert not any(
        "colab" in c["metadata"] or "outputId" in c["metadata"] for c in nb["cells"]
    )


def test_first_cell_is_the_papermill_parameters_cell_with_publish():
    first = _notebook()["cells"][0]
    assert "parameters" in first["metadata"].get("tags", [])
    assert "PUBLISH = True" in "".join(first["source"])


# --- end to end -----------------------------------------------------------

pm = pytest.importorskip("papermill")

SYDNEY_TODAY = datetime.now(pytz.timezone("Australia/Sydney")).date()
YESTERDAY = SYDNEY_TODAY - timedelta(days=1)


def _export(rows: list[tuple[str, str, float]]) -> pd.DataFrame:
    """A Betfair P/L export, with its real header names."""
    return pd.DataFrame(rows, columns=["Market", "Settled date", "Profit/Loss (AUD)"])


def _run(base: Path) -> None:
    pm.execute_notebook(
        str(NOTEBOOK),
        str(base / "out.ipynb"),
        parameters={
            "BASE_FOLDER": str(base),
            "MASTER_CSV": str(base / "Betfair_Master.csv"),
            "PUBLISH": False,
        },
        cwd=str(REPO),
        kernel_name="python3",
        progress_bar=False,
    )


@pytest.fixture
def clean_env(monkeypatch):
    # The notebook reads os.getenv for these first; a developer's .env must not leak in.
    for key in (
        "BASE_FOLDER",
        "MASTER_CSV",
        "GOOGLE_SHEET_NAME",
        "GOOGLE_SERVICE_ACCOUNT_JSON",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv(
        "PYTHONPATH", str(REPO) + os.pathsep + os.environ.get("PYTHONPATH", "")
    )


def test_pipeline_merges_archives_and_passes_safety_check(tmp_path, clean_env):
    y = f"{YESTERDAY:%Y-%m-%d}"
    _export(
        [
            (
                f"Horse Racing / Geraldton (AUS) {YESTERDAY.day}th : R1 1400m",
                f"{y} 13:00:00",
                12.5,
            ),
            (
                f"Greyhound Racing / Wentworth Park (AUS) {YESTERDAY.day}th : R2 520m",
                f"{y} 19:00:00",
                -4.0,
            ),
        ]
    ).to_csv(tmp_path / "BettingPandL_1.csv", index=False)

    _run(tmp_path)

    master = pd.read_csv(tmp_path / "Betfair_Master.csv", dtype=str)
    assert len(master) == 2
    assert sorted(master["Profit_Loss"].astype(float)) == [-4.0, 12.5]
    assert not list(tmp_path.glob("BettingPandL*.csv"))
    assert (tmp_path / "Archive" / "BettingPandL_1.csv").exists()

    out = json.loads((tmp_path / "out.ipynb").read_text(encoding="utf-8"))
    text = "".join(
        "".join(o.get("text", ""))
        for c in out["cells"]
        if c["cell_type"] == "code"
        for o in c["outputs"]
    )
    assert "PASS ✅" in text
    assert f"RAWS  → {YESTERDAY}: 8.50" in text  # the check really read the raw rows
    assert "skipped Google Sheets export" in text


def test_master_holding_earlier_bets_for_the_day_still_passes(tmp_path, clean_env):
    # A partial-day export: yesterday's morning bet came from an earlier run.
    y = f"{YESTERDAY:%Y-%m-%d}"
    pd.DataFrame(
        [("Horse Racing / Geraldton (AUS) 1st : R9 1000m", f"{y} 11:00:00", -100.0)],
        columns=["Market", "Settled date", "Profit_Loss"],
    ).to_csv(tmp_path / "Betfair_Master.csv", index=False)
    _export(
        [("Horse Racing / Geraldton (AUS) 1st : R1 1400m", f"{y} 13:00:00", 12.5)]
    ).to_csv(tmp_path / "BettingPandL_1.csv", index=False)
    _run(tmp_path)  # does not raise
    assert len(pd.read_csv(tmp_path / "Betfair_Master.csv", dtype=str)) == 2


def test_safety_check_stops_the_run_when_raw_rows_are_missing_from_master(
    tmp_path, clean_env
):
    # Two genuine identical bets in the export; the master already has one of them,
    # and Step 1's de-duplication drops both copies, so one bet never reaches it.
    y = f"{YESTERDAY:%Y-%m-%d}"
    bet = ("Horse Racing / Geraldton (AUS) 1st : R1 1400m", f"{y} 13:00:00", 5.0)
    pd.DataFrame([bet], columns=["Market", "Settled date", "Profit_Loss"]).to_csv(
        tmp_path / "Betfair_Master.csv", index=False
    )
    _export([bet, bet]).to_csv(tmp_path / "BettingPandL_1.csv", index=False)

    with pytest.raises(pm.PapermillExecutionError, match="1 raw row"):
        _run(tmp_path)

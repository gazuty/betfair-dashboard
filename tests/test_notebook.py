"""Checks on the committed notebook itself, and an end-to-end run of Steps 0–7."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import pytest

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

# A fixed past day keeps these tests independent of the clock (the summary
# check's yesterday/today totals are informational only).
DAY = "2025-08-09"
GERALDTON = "Horse Racing / Geraldton (AUS) 9th Aug : R1 1400m"
WENTWORTH = "Greyhound Racing / Wentworth Park (AUS) 9th Aug : R2 520m"


def _export(path: Path, rows: list[tuple[str, str, float]]) -> None:
    """Write a Betfair P/L export, with its real header names."""
    pd.DataFrame(rows, columns=["Market", "Settled date", "Profit/Loss (AUD)"]).to_csv(
        path, index=False
    )


def _master(path: Path, rows: list[tuple[str, str, float]]) -> None:
    pd.DataFrame(rows, columns=["Market", "Settled date", "Profit_Loss"]).to_csv(
        path, index=False
    )


def _run(base: Path, master: Path | None = None) -> str:
    """Run the notebook without publishing; return its printed output."""
    out_path = base / "out.ipynb"
    pm.execute_notebook(
        str(NOTEBOOK),
        str(out_path),
        parameters={
            "BASE_FOLDER": str(base),
            "MASTER_CSV": str(master or base / "Betfair_Master.csv"),
            "PUBLISH": False,
        },
        cwd=str(REPO),
        kernel_name="python3",
        progress_bar=False,
    )
    out = json.loads(out_path.read_text(encoding="utf-8"))
    return "".join(
        "".join(o.get("text", ""))
        for c in out["cells"]
        if c["cell_type"] == "code"
        for o in c["outputs"]
    )


def _master_rows(base: Path) -> pd.DataFrame:
    return pd.read_csv(base / "Betfair_Master.csv", dtype=str)


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


def test_first_run_builds_master_archives_exports_and_skips_publishing(
    tmp_path, clean_env
):
    _export(
        tmp_path / "BettingPandL_1.csv",
        [(GERALDTON, f"{DAY} 13:00:00", 12.5), (WENTWORTH, f"{DAY} 19:00:00", -4.0)],
    )

    text = _run(tmp_path)

    assert sorted(_master_rows(tmp_path)["Profit_Loss"].astype(float)) == [-4.0, 12.5]
    assert not list(tmp_path.glob("BettingPandL*.csv"))
    assert (tmp_path / "Archive" / "BettingPandL_1.csv").exists()
    assert "Verified: all 2 exported bet(s) are in the master" in text
    assert "PASS ✅" in text
    assert "skipped Google Sheets export" in text


def test_rejected_export_stays_in_place_while_accepted_ones_are_archived(
    tmp_path, clean_env
):
    _export(tmp_path / "BettingPandL_good.csv", [(GERALDTON, f"{DAY} 13:00:00", 12.5)])
    # A file with no profit column is rejected; archiving it would lose its bets.
    pd.DataFrame(
        [(WENTWORTH, f"{DAY} 19:00:00")], columns=["Market", "Settled date"]
    ).to_csv(tmp_path / "BettingPandL_bad.csv", index=False)

    text = _run(tmp_path)

    assert (tmp_path / "Archive" / "BettingPandL_good.csv").exists()
    assert (tmp_path / "BettingPandL_bad.csv").exists()
    assert not (tmp_path / "Archive" / "BettingPandL_bad.csv").exists()
    assert "Left 1 rejected file(s) in place, not archived: BettingPandL_bad.csv" in text
    assert len(_master_rows(tmp_path)) == 1


def test_partial_day_export_adds_to_earlier_bets_for_that_day(tmp_path, clean_env):
    _master(
        tmp_path / "Betfair_Master.csv",
        [(GERALDTON.replace("R1", "R9"), f"{DAY} 11:00:00", -100.0)],
    )
    _export(tmp_path / "BettingPandL_1.csv", [(GERALDTON, f"{DAY} 13:00:00", 12.5)])
    _run(tmp_path)
    assert len(_master_rows(tmp_path)) == 2


def test_overlapping_exports_add_a_shared_bet_once(tmp_path, clean_env):
    shared = (GERALDTON, f"{DAY} 13:00:00", 12.5)
    _export(tmp_path / "BettingPandL_1.csv", [shared])
    _export(
        tmp_path / "BettingPandL_2.csv", [shared, (WENTWORTH, f"{DAY} 19:00:00", -4.0)]
    )
    _run(tmp_path)
    assert sorted(_master_rows(tmp_path)["Profit_Loss"].astype(float)) == [-4.0, 12.5]


def test_overlapping_exports_of_a_bet_already_in_master_do_not_stop_the_run(
    tmp_path, clean_env
):
    shared = (GERALDTON, f"{DAY} 13:00:00", 12.5)
    _master(tmp_path / "Betfair_Master.csv", [shared])
    _export(tmp_path / "BettingPandL_1.csv", [shared])
    _export(tmp_path / "BettingPandL_2.csv", [shared])
    assert "PASS ✅" in _run(tmp_path)
    assert len(_master_rows(tmp_path)) == 1


def test_repeated_identical_bet_in_one_export_is_kept(tmp_path, clean_env):
    # Two genuine equal bets; the master already had one. The old de-duplication
    # dropped both copies, so one bet never reached the master.
    bet = (GERALDTON, f"{DAY} 13:00:00", 5.0)
    _master(tmp_path / "Betfair_Master.csv", [bet])
    _export(tmp_path / "BettingPandL_1.csv", [bet, bet])
    _run(tmp_path)
    assert len(_master_rows(tmp_path)) == 2


def test_non_iso_export_dates_are_recognised_against_the_master(tmp_path, clean_env):
    # Exports may use a day-month-year style; the master stores ISO. Same bet, same key.
    _master(tmp_path / "Betfair_Master.csv", [(GERALDTON, f"{DAY} 13:00:00", 12.5)])
    _export(tmp_path / "BettingPandL_1.csv", [(GERALDTON, "09-Aug-25 13:00", 12.5)])
    text = _run(tmp_path)
    assert (
        "1 bet(s) across 1 file(s)" in text
    )  # the date parsed; the row was not dropped
    assert "0 new row(s) for the master" in text
    assert len(_master_rows(tmp_path)) == 1


def test_unreadable_and_comma_formatted_pl_are_kept_and_reported(tmp_path, clean_env):
    path = tmp_path / "BettingPandL_1.csv"
    path.write_text(
        "Market,Settled date,Profit/Loss (AUD)\n"
        f'{GERALDTON},{DAY} 13:00:00,"1,234.50"\n'
        f"{WENTWORTH},{DAY} 19:00:00,\n",
        encoding="utf-8",
    )
    text = _run(tmp_path)
    pl = _master_rows(tmp_path).set_index("Market")["Profit_Loss"]
    assert float(pl[GERALDTON]) == 1234.5
    assert pd.isna(pl[WENTWORTH])  # kept, blank, not silently dropped
    assert "1 row(s) in BettingPandL_1.csv have a P/L that could not be read" in text


def test_rerunning_the_same_export_with_a_blank_pl_adds_nothing(tmp_path, clean_env):
    # A blank P/L comes back from the master CSV as NaN; it must still match the
    # export's NaN, or every rerun would append the row again.
    rows = "Market,Settled date,Profit/Loss (AUD)\n" + f"{WENTWORTH},{DAY} 19:00:00,\n"
    (tmp_path / "BettingPandL_1.csv").write_text(rows, encoding="utf-8")
    _run(tmp_path)
    (tmp_path / "BettingPandL_2.csv").write_text(rows, encoding="utf-8")
    text = _run(tmp_path)
    assert "0 new row(s) for the master" in text
    assert len(_master_rows(tmp_path)) == 1


def test_a_failed_master_write_leaves_master_and_exports_untouched(tmp_path, clean_env):
    # The new master is written to a temporary file first. If that fails, the real
    # master must be unchanged and the exports must stay for the next run.
    master = tmp_path / "Betfair_Master.csv"
    _master(master, [(WENTWORTH, f"{DAY} 19:00:00", -4.0)])
    before = master.read_text(encoding="utf-8")
    (tmp_path / "Betfair_Master.csv.tmp").mkdir()  # the write cannot succeed
    _export(tmp_path / "BettingPandL_1.csv", [(GERALDTON, f"{DAY} 13:00:00", 12.5)])

    with pytest.raises(pm.PapermillExecutionError):
        _run(tmp_path)

    assert master.read_text(encoding="utf-8") == before
    assert (tmp_path / "BettingPandL_1.csv").exists()
    assert not (tmp_path / "Archive" / "BettingPandL_1.csv").exists()

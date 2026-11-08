"""Unit tests for the helpers the notebook uses to check and publish data."""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import pytest

from sheets_export import (
    daily_totals,
    ensure_grid,
    pick_profit_column,
    retry_on_quota,
    to_sheet_values,
    rows_missing_from_master,
)


class FakeAPIError(Exception):
    """Stands in for gspread's APIError: carries a response with a status code."""

    def __init__(self, status: int):
        super().__init__(f"APIError: [{status}]")
        self.response = type("Response", (), {"status_code": status})()


class FakeWorksheet:
    def __init__(self, rows: int, cols: int):
        self.row_count, self.col_count = rows, cols
        self.resizes: list[tuple[int, int]] = []

    def resize(self, rows: int, cols: int) -> None:
        self.resizes.append((rows, cols))
        self.row_count, self.col_count = rows, cols


# --- pick_profit_column ---------------------------------------------------


def test_pick_profit_column_matches_betfair_export_header():
    assert (
        pick_profit_column(["Market", "Settled date", "Profit/Loss (AUD)"])
        == "Profit/Loss (AUD)"
    )


def test_pick_profit_column_prefers_aud():
    assert (
        pick_profit_column(["Profit (GBP)", "Profit/Loss (AUD)"]) == "Profit/Loss (AUD)"
    )


def test_pick_profit_column_none_when_absent():
    assert pick_profit_column(["Market", "Settled date"]) is None


# --- to_sheet_values ------------------------------------------------------


def test_numbers_stay_numbers_and_dates_become_iso():
    # The shape Step 4 builds for 'By Day': datetime64 Day, float P/L.
    frame = pd.DataFrame(
        {
            "Day": pd.to_datetime(["2025-08-09", "2025-08-10"]),
            "Profit_Loss": np.array([529.214, -172.4]),
            "Bets": np.array([3, 4], dtype="int64"),
        }
    )
    header, *rows = to_sheet_values(frame)
    assert header == ["'Day", "'Profit_Loss", "'Bets"]
    assert rows == [["2025-08-09", 529.21, 3], ["2025-08-10", -172.4, 4]]
    assert all(type(r[1]) is float and type(r[2]) is int for r in rows)


def test_python_dates_from_groupby_become_iso():
    # sport_daily groups on .dt.date, so its Day column holds datetime.date objects.
    header, row = to_sheet_values(pd.DataFrame({"Day": [dt.date(2025, 8, 10)]}))
    assert row == ["2025-08-10"]


def test_text_is_forced_to_text_including_formula_and_number_lookalikes():
    frame = pd.DataFrame(
        {"Track_Name": ["Geraldton", "=HYPERLINK(1)", "2025-08", "-5"]}
    )
    _, *rows = to_sheet_values(frame)
    assert [r[0] for r in rows] == ["'Geraldton", "'=HYPERLINK(1)", "'2025-08", "'-5"]


def test_missing_values_become_empty_cells():
    frame = pd.DataFrame({"a": [np.nan], "b": [None], "c": [pd.NaT]}).astype(
        {"c": "datetime64[ns]"}
    )
    _, row = to_sheet_values(frame)
    assert row == ["", "", ""]


def test_timestamp_with_time_keeps_time():
    _, row = to_sheet_values(pd.DataFrame({"t": [pd.Timestamp("2025-08-10 14:05:00")]}))
    assert row == ["2025-08-10 14:05:00"]


# --- retry_on_quota -------------------------------------------------------


def test_retry_returns_after_transient_quota_errors():
    calls = iter([FakeAPIError(429), FakeAPIError(429), "ok"])
    sleeps: list[float] = []

    def fn():
        result = next(calls)
        if isinstance(result, Exception):
            raise result
        return result

    assert retry_on_quota(fn, error_type=FakeAPIError, sleep=sleeps.append) == "ok"
    assert sleeps == [3.0, 6.0]


def test_retry_reraises_last_quota_error_instead_of_returning_none():
    attempts = 0

    def always_quota():
        nonlocal attempts
        attempts += 1
        raise FakeAPIError(429)

    with pytest.raises(FakeAPIError):
        retry_on_quota(always_quota, error_type=FakeAPIError, sleep=lambda _: None)
    assert attempts == 6


def test_retry_raises_other_api_errors_immediately():
    attempts = 0

    def forbidden():
        nonlocal attempts
        attempts += 1
        raise FakeAPIError(403)

    with pytest.raises(FakeAPIError):
        retry_on_quota(forbidden, error_type=FakeAPIError, sleep=lambda _: None)
    assert attempts == 1


def test_retry_passes_arguments_through():
    assert retry_on_quota(lambda a, *, b: a + b, 1, b=2, error_type=FakeAPIError) == 3


# --- ensure_grid ----------------------------------------------------------


def test_ensure_grid_grows_a_sheet_too_small_for_the_export():
    ws = FakeWorksheet(rows=200, cols=26)
    ensure_grid(ws, n_rows=223, n_cols=3)
    assert ws.resizes == [(223, 26)]


def test_ensure_grid_leaves_a_big_enough_sheet_alone():
    ws = FakeWorksheet(rows=500, cols=26)
    ensure_grid(ws, n_rows=223, n_cols=3)
    assert ws.resizes == []


# --- daily_totals / rows_missing_from_master----------------------------------

Y, T = dt.date(2025, 8, 9), dt.date(2025, 8, 10)


def _rows(*pairs: tuple[str, float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Settled date": pd.to_datetime([d for d, _ in pairs]),
            "Profit_Loss": [p for _, p in pairs],
        }
    )


def test_daily_totals_sums_per_day_and_zero_for_missing_days():
    frame = _rows(
        ("2025-08-09 13:00", 10.0),
        ("2025-08-09 15:00", -2.5),
        ("2025-08-08 10:00", 99.0),
    )
    assert daily_totals(frame, [Y, T]) == {Y: 7.5, T: 0.0}


def test_daily_totals_accepts_string_typed_csv_columns():
    frame = pd.DataFrame(
        {"Settled date": ["2025-08-09 13:00:00", "bad"], "Profit_Loss": ["4.5", ""]}
    )
    assert daily_totals(frame, [Y]) == {Y: 4.5}


def _bets(*rows: tuple[str, str, float]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["Market", "Settled date", "Profit_Loss"])


def test_nothing_missing_when_master_holds_every_raw_row_plus_earlier_bets():
    raw = _bets(("R1", "2025-08-09 13:00:00", 12.5))
    master = _bets(
        ("R0", "2025-08-09 11:00:00", -100.0), ("R1", "2025-08-09 13:00:00", 12.5)
    )
    assert rows_missing_from_master(master, raw).empty


def test_reports_a_raw_row_absent_from_the_master():
    raw = _bets(
        ("R1", "2025-08-09 13:00:00", 12.5), ("R2", "2025-08-09 14:00:00", -3.0)
    )
    master = _bets(("R1", "2025-08-09 13:00:00", 12.5))
    missing = rows_missing_from_master(master, raw)
    assert missing[["Market", "missing"]].values.tolist() == [["R2", 1]]


def test_counts_identical_bets_separately():
    # Two genuine identical bets in one export, only one in the master.
    raw = _bets(("R1", "2025-08-09 13:00:00", 5.0), ("R1", "2025-08-09 13:00:00", 5.0))
    master = _bets(("R1", "2025-08-09 13:00:00", 5.0))
    assert rows_missing_from_master(master, raw)["missing"].tolist() == [1]


def test_matches_master_read_back_as_strings():
    # The master is a CSV round trip: everything comes back as text.
    raw = _bets(("R1", "2025-08-09 13:00:00", 12.5))
    master = pd.DataFrame(
        {
            "Market": ["R1"],
            "Settled date": ["2025-08-09 13:00:00"],
            "Profit_Loss": ["12.50"],
        }
    )
    assert rows_missing_from_master(master, raw).empty


def test_empty_raws_have_nothing_missing():
    assert rows_missing_from_master(
        _bets(("R1", "2025-08-09 13:00:00", 1.0)), _bets()
    ).empty

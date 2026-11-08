"""Helpers the dashboard notebook uses to check its data and publish to Google Sheets.

They live in a module rather than in notebook cells so they can be unit tested.
The notebook imports them; Papermill runs it from the repo root, so a plain
``import sheets_export`` resolves.
"""

from __future__ import annotations

import datetime as dt
import math
import time
from collections.abc import Callable, Iterable
from typing import Any, TypeVar

import pandas as pd

T = TypeVar("T")

# Characters that make Google Sheets treat a USER_ENTERED string as a formula
# or a number. Text cells are written with a leading apostrophe so they stay
# text whatever they start with.
_TEXT_PREFIX = "'"

QUOTA_RETRY_ATTEMPTS = 6


def pick_profit_column(columns: Iterable[str]) -> str | None:
    """Return the profit column of a Betfair P/L export, or None if it has none.

    Betfair names it ``Profit/Loss (AUD)`` (currency varies). Any column whose
    name contains "profit" qualifies; one mentioning AUD wins if present.
    """
    candidates = [c for c in columns if "profit" in c.lower()]
    if not candidates:
        return None
    return next((c for c in candidates if "aud" in c.lower()), candidates[0])


def _cell_value(value: Any) -> Any:
    """Convert one pandas cell into what the Sheets API should receive.

    Numbers go as numbers so charts, number formats and formulas work; dates go
    as ISO strings, which USER_ENTERED parses into real dates; everything else
    is forced to text. Missing values become empty cells.
    """
    if value is None or value is pd.NaT:
        return ""
    if isinstance(value, bool):
        return value
    if isinstance(value, (pd.Timestamp, dt.datetime)):
        if value.time() == dt.time(0, 0):
            return value.strftime("%Y-%m-%d")
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, (int, float)) or hasattr(value, "item"):
        number = value.item() if hasattr(value, "item") else value
        if isinstance(number, float):
            if math.isnan(number):
                return ""
            return round(number, 2)
        return number
    return _TEXT_PREFIX + str(value)


def to_sheet_values(frame: pd.DataFrame) -> list[list[Any]]:
    """Return the header row plus data rows, ready for ``value_input_option="USER_ENTERED"``."""
    header = [_TEXT_PREFIX + str(c) for c in frame.columns]
    rows = [
        [_cell_value(v) for v in row]
        for row in frame.itertuples(index=False, name=None)
    ]
    return [header, *rows]


def _is_quota_error(error: Exception) -> bool:
    response = getattr(error, "response", None)
    status = getattr(response, "status_code", None)
    if status is not None:
        return status == 429
    return "429" in str(error)


def retry_on_quota(
    fn: Callable[..., T],
    *args: Any,
    error_type: type[Exception],
    attempts: int = QUOTA_RETRY_ATTEMPTS,
    sleep: Callable[[float], None] = time.sleep,
    **kwargs: Any,
) -> T:
    """Call ``fn``, backing off on Sheets quota (HTTP 429) errors.

    Other errors are raised at once. After ``attempts`` quota failures the last
    one is raised, so the run fails loudly instead of reporting stale data as
    published.
    """
    delay = 3.0
    for attempt in range(1, attempts + 1):
        try:
            return fn(*args, **kwargs)
        except error_type as error:
            if not _is_quota_error(error) or attempt == attempts:
                raise
            print(f"⏳ Hit Sheets quota; retrying in {delay:.0f}s…")
            sleep(delay)
            delay = min(delay * 2, 30.0)
    raise AssertionError("unreachable: the loop returns or raises")


def ensure_grid(worksheet: Any, n_rows: int, n_cols: int) -> None:
    """Grow ``worksheet`` so ``n_rows`` x ``n_cols`` values fit; never shrink it.

    The Sheets API rejects an update that runs past the grid, which is what broke
    first-time exports of tables longer than the old fixed 200 rows.
    """
    rows = max(worksheet.row_count, n_rows)
    cols = max(worksheet.col_count, n_cols)
    if (rows, cols) != (worksheet.row_count, worksheet.col_count):
        worksheet.resize(rows=rows, cols=cols)


def daily_totals(frame: pd.DataFrame, days: Iterable[dt.date]) -> dict[dt.date, float]:
    """Sum ``Profit_Loss`` per settled day, for the given days only."""
    settled = pd.to_datetime(frame["Settled date"], errors="coerce").dt.date
    profit = pd.to_numeric(frame["Profit_Loss"], errors="coerce")
    return {day: round(float(profit[settled == day].sum()), 2) for day in days}


def _bet_keys(frame: pd.DataFrame) -> pd.Series:
    """Count each (market, settled time, P/L) combination; the identity Step 1 deduplicates on."""
    keys = pd.DataFrame(
        {
            "Market": frame["Market"].astype(str),
            "Settled": pd.to_datetime(frame["Settled date"], errors="coerce"),
            "Profit_Loss": pd.to_numeric(frame["Profit_Loss"], errors="coerce").round(
                2
            ),
        }
    ).dropna(subset=["Settled"])
    return keys.value_counts()


def rows_missing_from_master(master: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    """Return the raw rows the master does not hold, with how many copies are missing.

    Every row of a merged export must be in the master at least as often as it is
    in the export. Comparing day totals cannot prove that: the master also holds
    earlier bets for the same day, which may be wins or losses.
    """
    raw_counts = _bet_keys(raw)
    master_counts = _bet_keys(master).reindex(raw_counts.index, fill_value=0)
    short = (raw_counts - master_counts).clip(lower=0)
    return short[short > 0].rename("missing").reset_index()

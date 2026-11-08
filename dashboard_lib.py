"""Helpers the dashboard notebook uses to merge exports, check them, and publish to Google Sheets.

They live in a module rather than in notebook cells so they can be unit tested.
The notebook imports them; Papermill runs it from the repo root, so a plain
``import dashboard_lib`` resolves.

A bet is identified by (market, settled time, P/L rounded to cents). Identical
rows inside one export are separate bets (two equal stakes on one runner);
identical rows in two different exports are the same bet downloaded twice
(overlapping date ranges).
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


# "1,234.50" or "-12,345": commas every three digits, dot decimal.
_THOUSANDS = r"-?\d{1,3}(?:,\d{3})+(?:\.\d+)?"


def parse_money(values: pd.Series) -> pd.Series:
    """Parse a P/L column to floats, accepting thousands separators ("1,234.50").

    Commas are removed only where they form a real thousands pattern, so a
    decimal comma ("12,50") is not misread as 1250; it, and anything else
    unreadable, becomes NaN and the caller reports how many.
    """
    if pd.api.types.is_numeric_dtype(values):
        return values.astype(float)
    text = values.astype("string").str.strip()
    thousands = text.str.fullmatch(_THOUSANDS, na=False)
    cleaned = text.where(~thousands, text.str.replace(",", "", regex=False))
    return pd.to_numeric(cleaned, errors="coerce").astype(float)


def _cell_value(value: Any) -> Any:
    """Convert one pandas cell into what the Sheets API should receive.

    Numbers go as numbers so charts, number formats and formulas work; dates go
    as ISO strings, which USER_ENTERED parses into real dates; everything else
    is forced to text. Missing values become empty cells.
    """
    if value is None or value is pd.NaT or value is pd.NA:
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


BET_COLUMNS = ["Market", "Settled date", "Profit_Loss"]


def _bet_keys(frame: pd.DataFrame) -> pd.Series:
    """Count how many times each bet identity occurs in ``frame``."""
    keys = pd.DataFrame(
        {
            "Market": frame["Market"].astype(str),
            "Settled date": pd.to_datetime(frame["Settled date"], errors="coerce"),
            "Profit_Loss": pd.to_numeric(frame["Profit_Loss"], errors="coerce").round(
                2
            ),
        }
    ).dropna(subset=["Settled date"])
    if keys.empty:
        index = pd.MultiIndex.from_arrays(
            [
                pd.Series(dtype=str),
                pd.Series(dtype="datetime64[ns]"),
                pd.Series(dtype=float),
            ],
            names=BET_COLUMNS,
        )
        return pd.Series(dtype="int64", index=index, name="count")
    # dropna=False: a bet whose P/L could not be read is still a bet.
    # Dropping it here would make it vanish from the master with nothing reported.
    return keys.value_counts(dropna=False)


def _expand(counts: pd.Series) -> pd.DataFrame:
    """Turn ``{bet identity: n}`` back into n rows per bet."""
    counts = counts[counts > 0]
    rows = counts.index.to_frame(index=False)
    rows = rows.loc[rows.index.repeat(counts.to_numpy())][BET_COLUMNS]
    return rows.sort_values("Settled date", kind="stable").reset_index(drop=True)


def combine_exports(frames: Iterable[pd.DataFrame]) -> pd.DataFrame:
    """Combine several exports, keeping each bet as many times as the export that has it most.

    A bet in two overlapping downloads is counted once; two identical bets in one
    download stay two.
    """
    counts = [_bet_keys(f) for f in frames]
    if not counts:
        return _expand(_bet_keys(pd.DataFrame(columns=BET_COLUMNS)))
    return _expand(pd.concat(counts).groupby(level=list(range(3)), dropna=False).max())


def rows_to_add(master: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    """Return the raw rows the master does not yet hold (as many copies as are short)."""
    raw_counts = _bet_keys(raw)
    master_counts = _bet_keys(master).reindex(raw_counts.index, fill_value=0)
    return _expand(raw_counts - master_counts)


def rows_missing_from_master(master: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    """Return the raw rows the master does not hold, with how many copies are missing.

    Used after saving, against the master as read back from disk: every row of a
    merged export must be in it at least as often as in the export. Comparing day
    totals cannot prove that, because the master also holds earlier bets for the
    same day, which may be wins or losses.
    """
    raw_counts = _bet_keys(raw)
    master_counts = _bet_keys(master).reindex(raw_counts.index, fill_value=0)
    short = (raw_counts - master_counts).clip(lower=0)
    return short[short > 0].rename("missing").reset_index()

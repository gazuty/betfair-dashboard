# scripts/update_sheets.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional, List
import os
import numpy as np
import pandas as pd

# We prefer pygsheets for simple DataFrame->Sheet writes
try:
    import pygsheets
except Exception as e:
    raise RuntimeError(
        "pygsheets is required. In Colab, run: %pip install -q pygsheets gspread oauth2client"
    ) from e


# -----------------------
# ---- Table builders ----
# -----------------------

def _ensure_daily(df: pd.DataFrame) -> pd.Series:
    if "settled_dt" not in df.columns or "pl_aud" not in df.columns:
        raise ValueError("Expected columns 'settled_dt' and 'pl_aud' in df")
    d = (
        df.dropna(subset=["settled_dt"])
          .assign(day=lambda x: x["settled_dt"].dt.tz_localize(None) if hasattr(x["settled_dt"].dt, "tz_localize") else x["settled_dt"])
          .assign(day=lambda x: x["settled_dt"].dt.date)
          .groupby("day", as_index=True)["pl_aud"]
          .sum()
          .sort_index()
    )
    d.index = pd.to_datetime(d.index)
    d.name = "daily_pl"
    return d


def _equity(daily: pd.Series) -> pd.Series:
    e = daily.cumsum()
    e.name = "equity"
    return e


def _drawdown_frame(equity: pd.Series) -> pd.DataFrame:
    roll_max = equity.cummax()
    dd = equity - roll_max
    with np.errstate(divide="ignore", invalid="ignore"):
        dd_pct = np.where(roll_max != 0, dd / roll_max, 0.0)
    return pd.DataFrame(
        {"equity": equity, "roll_max": roll_max, "drawdown": dd, "drawdown_pct": dd_pct},
        index=equity.index,
    )


def _longest_streak(mask_true: pd.Series) -> int:
    # mask_true: boolean Series (e.g., daily < 0)
    longest = cur = 0
    for v in mask_true.astype(bool).tolist():
        if v:
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 0
    return int(longest)


def _kpis(daily: pd.Series) -> pd.DataFrame:
    eq = _equity(daily)
    dd_df = _drawdown_frame(eq)

    total_pl = float(daily.sum())
    days = int(daily.shape[0])
    avg_daily = float(daily.mean()) if days else 0.0
    median_daily = float(daily.median()) if days else 0.0
    sr = float((daily > 0).mean()) if days else 0.0
    max_dd = float(dd_df["drawdown"].min()) if len(dd_df) else 0.0
    max_dd_pct = float(dd_df["drawdown_pct"].min()) if len(dd_df) else 0.0
    longest_loss = _longest_streak(daily < 0)
    longest_win = _longest_streak(daily > 0)

    rows = [
        ("Total P/L (AUD)", total_pl),
        ("Days", days),
        ("Average daily (AUD)", avg_daily),
        ("Median daily (AUD)", median_daily),
        ("Strike rate", sr),
        ("Max drawdown (AUD)", max_dd),
        ("Max drawdown (%)", max_dd_pct),
        ("Longest losing streak (days)", longest_loss),
        ("Longest winning streak (days)", longest_win),
    ]
    return pd.DataFrame(rows, columns=["Metric", "Value"])


def _by_day_table(daily: pd.Series) -> pd.DataFrame:
    eq = _equity(daily)
    out = pd.DataFrame({"Date": daily.index.date, "Daily P/L": daily.values, "Cumulative P/L": eq.values})
    return out


def _by_week_table(daily: pd.Series) -> pd.DataFrame:
    # Mark wants Sunday–Saturday. Use W-SUN labels for week end.
    weekly = daily.resample("W-SUN").sum()
    out = pd.DataFrame({"Week (ends Sun)": weekly.index.date, "Weekly P/L": weekly.values})
    return out


def _by_month_table(daily: pd.Series) -> pd.DataFrame:
    monthly = daily.resample("MS").sum()  # month start buckets
    out = pd.DataFrame({"Month": monthly.index.strftime("%Y-%m"), "Monthly P/L": monthly.values})
    return out


def _safe_group_sum(df: pd.DataFrame, col: str) -> Optional[pd.DataFrame]:
    if col not in df.columns:
        return None
    temp = df.copy()
    temp["day"] = temp["settled_dt"].dt.date
    g = temp.groupby(col, as_index=False)["pl_aud"].sum().sort_values("pl_aud", ascending=False)
    g.columns = [col, "Total P/L"]
    return g


# --------------------------------
# ---- Google Sheets utilities ----
# --------------------------------

def _authorize_with_pygsheets():
    """
    Preferred: Service account JSON via GOOGLE_APPLICATION_CREDENTIALS.
    Fallback: user OAuth flow (will prompt in Colab).
    """
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if creds_path and os.path.exists(creds_path):
        return pygsheets.authorize(service_file=creds_path)
    # fallback to local OAuth (opens a link to authorize)
    return pygsheets.authorize()


def _open_or_create_sheet(gc, sheet_name: str):
    try:
        return gc.open(sheet_name)
    except Exception:
        # Create new spreadsheet in Drive root if not found
        sh = gc.create(sheet_name)
        return sh


def _upsert_tab(spreadsheet, title: str, df: pd.DataFrame, freeze_rows: int = 1):
    # Create or fetch worksheet
    try:
        ws = spreadsheet.worksheet_by_title(title)
        ws.clear()
    except Exception:
        ws = spreadsheet.add_worksheet(title=title, rows=max(100, len(df) + 10), cols=max(10, len(df.columns) + 2))

    # Write with headers
    ws.set_dataframe(df, (1, 1), copy_head=True, extend=True)

    # Freeze header row
    try:
        ws.frozen_rows = freeze_rows
    except Exception:
        pass


# --------------------------------
# ---- Public entry point API ----
# --------------------------------

def update_google_sheets(df: pd.DataFrame, sheet_name: str):
    """
    Build summary tables from cleaned df and push them to Google Sheets.

    Expected df columns:
      - settled_dt (datetime64)
      - pl_aud (float)
      - optionally: sport, country, track (string)
    """
    # Build tables
    daily = _ensure_daily(df)
    tabs: Dict[str, pd.DataFrame] = {
        "By Day": _by_day_table(daily),
        "By Week": _by_week_table(daily),
        "By Month": _by_month_table(daily),
        "KPIs": _kpis(daily),
    }

    # Optional slices if available
    for col, title in [("sport", "By Sport"), ("country", "By Country"), ("track", "By Track")]:
        t = _safe_group_sum(df, col)
        if t is not None:
            tabs[title] = t

    # Authorize & open spreadsheet
    gc = _authorize_with_pygsheets()
    sh = _open_or_create_sheet(gc, sheet_name)

    # Upsert each tab
    for title, table in tabs.items():
        _upsert_tab(sh, title, table, freeze_rows=1)

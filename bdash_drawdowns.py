# bdash_drawdowns.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, Optional
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def _ensure_daily(df: pd.DataFrame) -> pd.Series:
    if "settled_dt" not in df.columns or "pl_aud" not in df.columns:
        raise ValueError("Expected columns 'settled_dt' and 'pl_aud'")
    daily = (
        df.dropna(subset=["settled_dt"])
          .assign(day=lambda x: x["settled_dt"].dt.date)
          .groupby("day", as_index=True)["pl_aud"]
          .sum()
          .sort_index()
    )
    daily.index = pd.to_datetime(daily.index)
    return daily

def _equity_series(daily: pd.Series) -> pd.Series:
    eq = daily.cumsum()
    eq.name = "equity"
    return eq

def _drawdown_series(equity: pd.Series) -> pd.DataFrame:
    roll_max = equity.cummax()
    dd = equity - roll_max
    dd_pct = np.where(roll_max != 0, dd / roll_max, 0.0)
    out = pd.DataFrame({"equity": equity, "roll_max": roll_max, "drawdown": dd, "drawdown_pct": dd_pct}, index=equity.index)
    return out

def _plot_series(y: pd.Series, title: str, out_path: Optional[Path] = None):
    plt.figure()
    plt.plot(y.index, y.values)  # do not set colors/styles (tooling rule)
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel(y.name if y.name else "")
    plt.tight_layout()
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out_path, dpi=150)
    plt.close()

def _plot_underwater(dd_df: pd.DataFrame, title: str, out_path: Optional[Path] = None):
    # underwater = drawdown percentage (negative values)
    uw = pd.Series(dd_df["drawdown_pct"], index=dd_df.index, name="drawdown_pct")
    plt.figure()
    plt.plot(uw.index, uw.values)
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("Drawdown (pct)")
    plt.tight_layout()
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out_path, dpi=150)
    plt.close()

def _rolling_metrics(daily: pd.Series) -> pd.DataFrame:
    wins = (daily > 0).astype(int)
    # Choose windows: 14, 28, 56 days (2/4/8 weeks)
    windows = [14, 28, 56]
    data = {
        "daily_pl": daily,
        "equity": daily.cumsum(),
        "win": wins,
        "rolling_mean_28": daily.rolling(28, min_periods=5).mean(),
        "rolling_std_28": daily.rolling(28, min_periods=5).std(),
        "rolling_sr_28": wins.rolling(28, min_periods=5).mean(),  # strike rate
        "rolling_sum_14": daily.rolling(14, min_periods=5).sum(),
        "rolling_sum_28": daily.rolling(28, min_periods=5).sum(),
        "rolling_sum_56": daily.rolling(56, min_periods=10).sum(),
    }
    df = pd.DataFrame(data)
    # simple Sharpe-like ratio on 28-day window (not annualized)
    with np.errstate(divide="ignore", invalid="ignore"):
        df["rolling_sharpe_28"] = df["rolling_mean_28"] / df["rolling_std_28"]
    return df

def build_risk_artifacts(df: pd.DataFrame, out_dir: str | Path) -> Dict[str, object]:
    """
    Creates:
      - equity curve PNG
      - underwater/drawdown PNG
      - worst_days CSV
      - rolling_metrics CSV
    Returns paths + dataframes for interactive use.
    """
    out_dir = Path(out_dir)
    daily = _ensure_daily(df)
    equity = _equity_series(daily)
    dd_df = _drawdown_series(equity)

    # Save charts
    equity_png = out_dir / "equity_curve.png"
    underwater_png = out_dir / "underwater_drawdown.png"
    _plot_series(equity, "Equity Curve (cumulative P/L)", equity_png)
    _plot_underwater(dd_df, "Underwater (drawdown % from peak)", underwater_png)

    # Worst 20 days (by P/L)
    worst_days = daily.sort_values().head(20).to_frame("pl_aud")
    worst_days_csv = out_dir / "worst_days.csv"
    worst_days.to_csv(worst_days_csv)

    # Rolling metrics
    roll = _rolling_metrics(daily)
    rolling_csv = out_dir / "rolling_metrics.csv"
    roll.to_csv(rolling_csv)

    return {
        "equity_png": str(equity_png),
        "underwater_png": str(underwater_png),
        "worst_days_csv": str(worst_days_csv),
        "rolling_csv": str(rolling_csv),
        "worst_days": worst_days,
        "rolling": roll,
        "daily": daily,
        "equity": equity,
        "drawdowns": dd_df,
    }

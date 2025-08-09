# bdash_drawdowns.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, Optional
import json
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
    daily.name = "pl_aud"
    return daily

def _equity_series(daily: pd.Series) -> pd.Series:
    eq = daily.cumsum()
    eq.name = "equity"
    return eq

def _drawdown_frame(equity: pd.Series) -> pd.DataFrame:
    roll_max = equity.cummax()
    dd = equity - roll_max
    with np.errstate(divide="ignore", invalid="ignore"):
        dd_pct = np.where(roll_max != 0, dd / roll_max, 0.0)
    out = pd.DataFrame(
        {"equity": equity, "roll_max": roll_max, "drawdown": dd, "drawdown_pct": dd_pct},
        index=equity.index,
    )
    return out

def _plot_line(series: pd.Series, title: str, ylabel: str, out_path: Optional[Path] = None):
    plt.figure()
    plt.plot(series.index, series.values)  # no explicit colors/styles
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel(ylabel)
    plt.tight_layout()
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out_path, dpi=150)
    plt.close()

def _plot_underwater(dd_df: pd.DataFrame, title: str, out_path: Optional[Path] = None):
    uw = pd.Series(dd_df["drawdown_pct"], index=dd_df.index, name="drawdown_pct")
    plt.figure()
    plt.plot(uw.index, uw.values)
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("Drawdown (fraction of peak)")
    plt.tight_layout()
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out_path, dpi=150)
    plt.close()

def _rolling_metrics(daily: pd.Series) -> pd.DataFrame:
    wins = (daily > 0).astype(int)
    out = pd.DataFrame(
        {
            "daily_pl": daily,
            "equity": daily.cumsum(),
            "win": wins,
            "rolling_sum_14": daily.rolling(14, min_periods=5).sum(),
            "rolling_sum_28": daily.rolling(28, min_periods=5).sum(),
            "rolling_sum_56": daily.rolling(56, min_periods=10).sum(),
            "rolling_mean_28": daily.rolling(28, min_periods=5).mean(),
            "rolling_std_28": daily.rolling(28, min_periods=5).std(),
            "rolling_sr_28": wins.rolling(28, min_periods=5).mean(),  # strike rate
        }
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        out["rolling_sharpe_28"] = out["rolling_mean_28"] / out["rolling_std_28"]
    return out

def _streaks(daily: pd.Series) -> Dict[str, int]:
    # Longest losing streak (consecutive days with daily < 0)
    is_loss = (daily < 0).astype(int).values
    longest = cur = 0
    for v in is_loss:
        if v == 1: 
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 0
    # Longest winning streak
    is_win = (daily > 0).astype(int).values
    longest_win = cur = 0
    for v in is_win:
        if v == 1:
            cur += 1
            longest_win = max(longest_win, cur)
        else:
            cur = 0
    return {"longest_losing_streak_days": int(longest), "longest_winning_streak_days": int(longest_win)}

def _max_drawdown(dd_df: pd.DataFrame) -> Dict[str, float]:
    # Most negative drawdown and its percent
    min_dd = float(dd_df["drawdown"].min()) if len(dd_df) else 0.0
    min_dd_pct = float(dd_df["drawdown_pct"].min()) if len(dd_df) else 0.0
    return {"max_drawdown": min_dd, "max_drawdown_pct": min_dd_pct}

def build_risk_artifacts(df: pd.DataFrame, out_dir: str | Path) -> Dict[str, object]:
    """
    Creates:
      - equity curve PNG
      - underwater/drawdown PNG
      - worst_days CSV (20 worst daily P/L)
      - rolling_metrics CSV (SR, rolling sums, volatility, sharpe-ish)
      - stats.json (headline risk stats)
    Returns paths + dataframes for interactive use.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    daily = _ensure_daily(df)
    equity = _equity_series(daily)
    dd_df = _drawdown_frame(equity)

    # Charts
    equity_png = out_dir / "equity_curve.png"
    underwater_png = out_dir / "underwater_drawdown.png"
    _plot_line(equity, "Equity Curve (cumulative P/L)", "P/L (AUD)", equity_png)
    _plot_underwater(dd_df, "Underwater (drawdown from peak)", underwater_png)

    # Worst days
    worst_days = daily.sort_values().head(20).to_frame("pl_aud")
    worst_days_csv = out_dir / "worst_days.csv"
    worst_days.to_csv(worst_days_csv)

    # Rolling metrics
    roll = _rolling_metrics(daily)
    rolling_csv = out_dir / "rolling_metrics.csv"
    roll.to_csv(rolling_csv)

    # Headline stats
    stats = {
        **_max_drawdown(dd_df),
        **_streaks(daily),
        "total_pl": float(daily.sum()),
        "days": int(daily.shape[0]),
        "avg_daily": float(daily.mean()) if daily.shape[0] else 0.0,
        "median_daily": float(daily.median()) if daily.shape[0] else 0.0,
    }
    stats_json = out_dir / "stats.json"
    stats_json.write_text(json.dumps(stats, indent=2))

    return {
        "equity_png": str(equity_png),
        "underwater_png": str(underwater_png),
        "worst_days_csv": str(worst_days_csv),
        "rolling_csv": str(rolling_csv),
        "stats_json": str(stats_json),
        "worst_days": worst_days,
        "rolling": roll,
        "daily": daily,
        "equity": equity,
        "drawdowns": dd_df,
        "stats": stats,
    }

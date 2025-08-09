# bdash_ingest.py
# ------------------------------------------------------------
# Ingest & clean Betfair CSVs → master.parquet + combined_cleaned.csv
# - Case-insensitive column normalization (COLMAP)
# - Robust money/date parsing (handles "(1.23)" negatives & currency symbols)
# - Dedupe with Bet ID fallback to hashed subset
# - Sorted earliest→latest by settled_dt, then placed_dt (defensive)
# - Quick daily/monthly rollups + equity column
# ------------------------------------------------------------
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

# ---- CONFIG: map raw CSV headers → canonical names used in this module ----
# We match case-insensitively at runtime; include common variants here.
COLMAP: Dict[str, str] = {
    # Dates
    "Settled date": "settled_dt",
    "Settled Date": "settled_dt",

    # "placed"/start time variants from Betfair exports
    "Bet placed": "placed_dt",
    "Bet Placed": "placed_dt",
    "Start time": "placed_dt",
    "Start Time": "placed_dt",
    "Start time (local)": "placed_dt",
    "Start Time (Local)": "placed_dt",

    # P/L & stake (AUD)
    "Profit/Loss (AUD)": "pl_aud",
    "Profit/Loss": "pl_aud",
    "P/L (AUD)": "pl_aud",
    "P/L": "pl_aud",
    "Stake (AUD)": "stake_aud",
    "Stake": "stake_aud",

    # Identifiers / descriptors
    "Bid type": "bid_type",
    "Bet type": "bid_type",
    "Bet ID": "bet_id",
    "BetID": "bet_id",
    "Market": "market",
    "Selection": "selection",
    "Event": "event",
    "Sport": "sport",
    "Country": "country",
    "Track Name": "track",
    "Venue": "track",
    "Odds": "odds",
    "Price": "odds",
}

# Regex helpers for money parsing
_money_pat = re.compile(r"[,\s$€£]")   # remove separators/currency
_paren_pat = re.compile(r"^\((.*)\)$") # "(1.23)" → negate


def clean_money(x) -> float | None:
    """Parse money-like strings reliably, supporting '(1.23)' as negative."""
    if pd.isna(x):
        return None
    s = str(x).strip()
    if s == "":
        return None
    m = _paren_pat.match(s)
    neg = False
    if m:
        s = m.group(1)
        neg = True
    s = _money_pat.sub("", s)
    s = s.replace("--", "-")
    try:
        val = float(s)
        return -val if neg else val
    except ValueError:
        return None


def parse_dt(s):
    """Coerce to pandas datetime with Betfair-friendly defaults."""
    if pd.isna(s) or str(s).strip() == "":
        return pd.NaT
    # Betfair CSVs are commonly "DD-MMM-YY HH:MM", e.g., "03-Aug-25 23:25"
    return pd.to_datetime(s, errors="coerce", dayfirst=True, utc=False)


def _case_insensitive_normalize(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize headers to canonical names using a case-insensitive map.
    Trims whitespace and matches keys by lower-cased names.
    """
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    cmap = {k.strip().lower(): v for (k, v) in COLMAP.items()}
    rename = {}
    for c in df.columns:
        key = str(c).strip().lower()
        if key in cmap:
            rename[c] = cmap[key]
    return df.rename(columns=rename)


def ensure_required(df: pd.DataFrame, required: List[str]) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def build_key_cols(df: pd.DataFrame) -> pd.Series:
    """
    Dedupe key:
      - Prefer bet_id if present/non-null.
      - Else hash a stable subset to avoid accidental collisions.
    """
    if "bet_id" in df.columns and df["bet_id"].notna().any():
        return df["bet_id"].astype(str)

    subset = ["market", "selection", "settled_dt", "stake_aud", "pl_aud"]
    present = [c for c in subset if c in df.columns]

    def _row_hash(row):
        raw = "||".join(str(row.get(c, "")) for c in present)
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    return df.apply(_row_hash, axis=1)


def load_csvs(folder: str | Path, pattern: str = "*.csv") -> Tuple[pd.DataFrame, List[Path]]:
    """
    Read all CSVs as strings first (so we control type coercion later).
    Returns concatenated DataFrame and list of file Paths.
    """
    paths = sorted(Path(folder).glob(pattern))
    if not paths:
        raise FileNotFoundError(f"No CSVs found in {folder} matching {pattern}")

    frames = []
    for p in paths:
        df = pd.read_csv(p, dtype=str, low_memory=False)
        df["__source_file"] = p.name
        frames.append(df)

    return pd.concat(frames, ignore_index=True), paths


def clean_and_coerce(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Normalize headers, parse dates/money, basic string tidy, and sort."""
    # Case-insensitive normalization
    df = _case_insensitive_normalize(df_raw)

    # Minimal required columns for downstream logic
    required = ["settled_dt", "pl_aud"]
    ensure_required(df, required)

    # Parse dates (safe-coerce)
    if "settled_dt" in df.columns:
        df["settled_dt"] = df["settled_dt"].map(parse_dt)
    # Ensure placed_dt ALWAYS exists to avoid KeyError later
    if "placed_dt" in df.columns:
        df["placed_dt"] = df["placed_dt"].map(parse_dt)
    else:
        df["placed_dt"] = pd.NaT

    # Money fields
    df["pl_aud"] = df["pl_aud"].map(clean_money)
    if "stake_aud" in df.columns:
        df["stake_aud"] = df["stake_aud"].map(clean_money)

    # Numeric odds if present
    if "odds" in df.columns:
        df["odds"] = pd.to_numeric(df["odds"], errors="coerce")

    # Basic tidy strings
    for c in ["bid_type", "market", "selection", "event", "sport", "country", "track", "__source_file"]:
        if c in df.columns:
            df[c] = df[c].astype("string").str.strip()

    # Defensive sort: even if placed_dt was missing originally, it now exists
    df = df.sort_values(["settled_dt", "placed_dt"], na_position="last").reset_index(drop=True)
    return df


def dedupe(df: pd.DataFrame) -> pd.DataFrame:
    key = build_key_cols(df)
    before = len(df)
    df = df.loc[~key.duplicated()].copy()
    after = len(df)
    df.attrs["deduped_rows"] = before - after
    return df


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Light derived columns used by downstream steps."""
    if "settled_dt" in df.columns:
        df["day"] = df["settled_dt"].dt.date
        df["month"] = df["settled_dt"].dt.to_period("M").astype(str)
        df["week"] = df["settled_dt"].dt.to_period("W").astype(str)
    if "pl_aud" in df.columns:
        df["equity"] = df["pl_aud"].cumsum()
    return df


def ingest_folder(
    folder: str | Path,
    pattern: str = "*.csv",
    master_parquet: str | Path = "master.parquet",
    export_clean_csv: str | Path | None = "combined_cleaned.csv",
):
    """
    Read, clean, dedupe, feature-ize; save Parquet master and optional clean CSV.
    Returns a dict with the cleaned df, simple rollups, and metadata.
    """
    raw, paths = load_csvs(folder, pattern)
    df = clean_and_coerce(raw)
    df = dedupe(df)
    df = add_features(df)

    # Persist typed master (fast reloads, stable dtypes)
    df.to_parquet(master_parquet, index=False)

    # Optional CSV for compatibility (e.g., Google Sheets)
    if export_clean_csv:
        df.to_csv(export_clean_csv, index=False)

    # Quick rollups (keep NaN dates if present)
    daily = df.groupby("day", dropna=False, as_index=False)["pl_aud"].sum()
    monthly = df.groupby("month", dropna=False, as_index=False)["pl_aud"].sum()

    return {
        "df": df,
        "daily": daily,
        "monthly": monthly,
        "files_processed": [p.name for p in paths],
        "deduped_rows": df.attrs.get("deduped_rows", 0),
        "rows": len(df),
        "master_parquet": str(master_parquet),
        "clean_csv": str(export_clean_csv) if export_clean_csv else None,
    }


# ---- If you run this file directly (optional quick smoke test) ----
if __name__ == "__main__":
    # Example:
    # python bdash_ingest.py /path/to/Betfair "*.csv" master.parquet combined_cleaned.csv
    import sys

    args = sys.argv[1:]
    folder = args[0] if len(args) > 0 else "."
    pattern = args[1] if len(args) > 1 else "*.csv"
    master = args[2] if len(args) > 2 else "master.parquet"
    clean_csv = args[3] if len(args) > 3 else "combined_cleaned.csv"

    out = ingest_folder(folder=folder, pattern=pattern, master_parquet=master, export_clean_csv=clean_csv)
    print(
        f"Processed {len(out['files_processed'])} files | rows={out['rows']} | "
        f"deduped={out['deduped_rows']}\nMaster: {out['master_parquet']} | Clean CSV: {out['clean_csv']}"
    )

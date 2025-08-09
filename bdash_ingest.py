# bdash_ingest.py
from __future__ import annotations
import re
import hashlib
from pathlib import Path
from typing import List, Dict, Tuple
import pandas as pd

# ---- CONFIG: map your canonical column names here ----
COLMAP = {
    # example mappings; adjust to your actual headers if they differ
    "Settled date": "settled_dt",
    "Bet placed": "placed_dt",
    "Profit/Loss (AUD)": "pl_aud",
    "Profit/Loss": "pl_aud",
    "Bid type": "bid_type",
    "Stake (AUD)": "stake_aud",
    "Market": "market",
    "Selection": "selection",
    "Bet ID": "bet_id",
    "Event": "event",
    "Sport": "sport",
    "Country": "country",
    "Track Name": "track",
    "Odds": "odds",
}

# ---- helpers ----
_money_pat = re.compile(r"[,\s$€£]")  # strip common currency junk
_paren_pat = re.compile(r"^\((.*)\)$")  # (1.23) => -1.23

def clean_money(x) -> float | None:
    if pd.isna(x):
        return None
    s = str(x).strip()
    if s == "":
        return None
    # treat parentheses as negative
    m = _paren_pat.match(s)
    neg = False
    if m:
        s = m.group(1)
        neg = True
    s = _money_pat.sub("", s)  # remove separators/currency
    s = s.replace("--", "-")
    try:
        val = float(s)
        return -val if neg else val
    except ValueError:
        return None

def parse_dt(s):
    if pd.isna(s) or str(s).strip() == "":
        return pd.NaT
    return pd.to_datetime(s, errors="coerce", dayfirst=False, utc=False)

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    # standardize to canonical column names when seen
    rename = {c: COLMAP.get(c, c) for c in df.columns}
    df = df.rename(columns=rename)
    return df

def ensure_required(df: pd.DataFrame, required: List[str]) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

def build_key_cols(df: pd.DataFrame) -> pd.Series:
    """
    Build a robust dedupe key. Prefer bet_id if present; otherwise hash a stable subset.
    """
    if "bet_id" in df.columns and df["bet_id"].notna().any():
        return df["bet_id"].astype(str)
    subset = ["market","selection","settled_dt","stake_aud","pl_aud"]
    present = [c for c in subset if c in df.columns]
    def _row_hash(row):
        raw = "||".join(str(row.get(c, "")) for c in present)
        return hashlib.md5(raw.encode("utf-8")).hexdigest()
    return df.apply(_row_hash, axis=1)

def load_csvs(folder: str | Path, pattern: str = "*.csv") -> Tuple[pd.DataFrame, List[Path]]:
    paths = sorted(Path(folder).glob(pattern))
    if not paths:
        raise FileNotFoundError(f"No CSVs found in {folder} matching {pattern}")
    frames = []
    for p in paths:
        df = pd.read_csv(p, dtype=str)  # read as string first; we’ll coerce explicitly
        df["__source_file"] = p.name
        frames.append(df)
    return pd.concat(frames, ignore_index=True), paths

def clean_and_coerce(df_raw: pd.DataFrame) -> pd.DataFrame:
    df = normalize_columns(df_raw)

    # minimal required fields for downstream logic
    required = ["settled_dt", "pl_aud"]
    ensure_required(df, required)

    # coerce dates and money
    if "settled_dt" in df.columns:
        df["settled_dt"] = df["settled_dt"].map(parse_dt)
    if "placed_dt" in df.columns:
        df["placed_dt"] = df["placed_dt"].map(parse_dt)

    df["pl_aud"] = df["pl_aud"].map(clean_money)
    if "stake_aud" in df.columns:
        df["stake_aud"] = df["stake_aud"].map(clean_money)

    # odds numeric if present
    for c in ["odds"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # basic tidy strings
    for c in ["bid_type","market","selection","event","sport","country","track","__source_file"]:
        if c in df.columns:
            df[c] = df[c].astype("string").str.strip()

    # sort (earliest first)
    df = df.sort_values(["settled_dt","placed_dt"], na_position="last").reset_index(drop=True)
    return df

def dedupe(df: pd.DataFrame) -> pd.DataFrame:
    key = build_key_cols(df)
    before = len(df)
    df = df.loc[~key.duplicated()].copy()
    after = len(df)
    df.attrs["deduped_rows"] = before - after
    return df

def add_features(df: pd.DataFrame) -> pd.DataFrame:
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
) -> Dict[str, object]:
    raw, paths = load_csvs(folder, pattern)
    df = clean_and_coerce(raw)
    df = dedupe(df)
    df = add_features(df)

    # persist parquet (typed master)
    df.to_parquet(master_parquet, index=False)

    # optional CSV for compatibility (Sheets, etc.)
    if export_clean_csv:
        df.to_csv(export_clean_csv, index=False)

    # quick rollups you already use
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

# bdash_ingest.py  (v0.3.4)
# ------------------------------------------------------------
# Ingest & clean Betfair CSVs → master.parquet + combined_cleaned.csv
# - Case-insensitive column normalization (COLMAP)
# - Coalesce duplicate-named columns (leftmost non-null per row)
# - Robust money/date parsing (handles "(1.23)" negatives & currency symbols)
# - Dedupe with Bet ID fallback to hashed subset
# - Sort by settled_dt only (placed_dt optional; never required)
# - Quick daily/monthly rollups + equity column
# ------------------------------------------------------------
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

__BDASH_INGEST_VERSION__ = "0.3.4"

# ---- CONFIG: raw header → canonical name (matched case-insensitively) ----
COLMAP: Dict[str, str] = {
    # Dates
    "Settled date": "settled_dt",
    "Settled Date": "settled_dt",

    # placed/start time variants
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

# --- money parsing helpers ---
_money_pat = re.compile(r"[,\s$€£]")
_paren_pat = re.compile(r"^\((.*)\)$")


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
    s = _money_pat.sub("", s).replace("--", "-")
    try:
        val = float(s)
        return -val if neg else val
    except ValueError:
        return None


def parse_dt(s):
    """Coerce to pandas datetime; try common Betfair formats first, then fallback."""
    if pd.isna(s) or str(s).strip() == "":
        return pd.NaT
    s = str(s).strip()
    for fmt in ("%d-%b-%y %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return pd.to_datetime(s, format=fmt)
        except (ValueError, TypeError):
            pass
    return pd.to_datetime(s, errors="coerce", dayfirst=True, utc=False)


def _case_insensitive_normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize headers to canonical names using a case-insensitive map."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    cmap = {k.strip().lower(): v for (k, v) in COLMAP.items()}
    rename = {}
    for c in df.columns:
        key = str(c).strip().lower()
        if key in cmap:
            rename[c] = cmap[key]
    return df.rename(columns=rename)


def _coalesce_duplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    If multiple columns share the same name, coalesce them into one:
    take the first non-null value across duplicates for each row.
    """
    if df.columns.duplicated().any():
        out = pd.DataFrame(index=df.index)
        seen = set()
        for col in df.columns:
            if col in seen:
                continue
            same = [c for c in df.columns if c == col]
            if len(same) == 1:
                out[col] = df[col]
            else:
                # left-to-right coalesce
                out[col] = df[same].bfill(axis=1).iloc[:, 0]
            seen.add(col)
        return out
    return df


def ensure_required(df: pd.DataFrame, required: List[str]) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")


def build_key_cols(df: pd.DataFrame) -> pd.Series:
    """Dedupe key: prefer bet_id; else hash a stable subset."""
    if "bet_id" in df.columns and df["bet_id"].notna().any():
        return df["bet_id"].astype(str)
    subset = ["market", "selection", "settled_dt", "stake_aud", "pl_aud"]
    present = [c for c in subset if c in df.columns]

    def _row_hash(row):
        raw = "||".join(str(row.get(c, "")) for c in present)
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    return df.apply(_row_hash, axis=1)


def load_csvs(folder: str | Path, pattern: str = "*.csv") -> Tuple[pd.DataFrame, List[Path]]:
    """Read all CSVs as strings first (so we control type coercion later)."""
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
    """Normalize headers, coalesce duplicates, parse dates/money, tidy, and sort."""
    # 1) header normalisation
    df = _case_insensitive_normalize(df_raw)
    # 2) coalesce duplicate-named columns BEFORE anything else
    df = _coalesce_duplicate_columns(df)

    # Required
    ensure_required(df, ["settled_dt", "pl_aud"])

    # Dates
    df["settled_dt"] = df["settled_dt"].map(parse_dt)
    if "placed_dt" in df.columns:
        df["placed_dt"] = df["placed_dt"].map(parse_dt)
    else:
        df["placed_dt"] = pd.NaT  # present but optional

    # Money
    df["pl_aud"] = df["pl_aud"].map(clean_money)
    if "stake_aud" in df.columns:
        df["stake_aud"] = df["stake_aud"].map(clean_money)

    # Numerics
    if "odds" in df.columns:
        df["odds"] = pd.to_numeric(df["odds"], errors="coerce")

    # Strings (safe now that duplicates were collapsed)
    for c in ["bid_type", "market", "selection", "event", "sport", "country", "track", "__source_file"]:
        if c in df.columns:
            df[c] = df[c].astype("string").str.strip()

    # Sort strictly by settled_dt (placed_dt not required)
    df = df.sort_values(["settled_dt"], na_position="last").reset_index(drop=True)
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
):
    """Read, clean, dedupe, feature-ize; save Parquet master and optional clean CSV."""
    raw, paths = load_csvs(folder, pattern)
    df = clean_and_coerce(raw)
    df = dedupe(df)
    df = add_features(df)

    df.to_parquet(master_parquet, index=False)
    if export_clean_csv:
        df.to_csv(export_cleaned_csv := export_clean_csv, index=False)
    else:
        export_cleaned_csv = None

    daily = df.groupby("day", dropna=False, as_index=False)["pl_aud"].sum()
    monthly = df.groupby("month", dropna=False, as_index=False)["pl_aud"].sum()

    return {
        "version": __BDASH_INGEST_VERSION__,
        "df": df,
        "daily": daily,
        "monthly": monthly,
        "files_processed": [p.name for p in paths],
        "deduped_rows": df.attrs.get("deduped_rows", 0),
        "rows": len(df),
        "master_parquet": str(master_parquet),
        "clean_csv": str(export_cleaned_csv) if export_cleaned_csv else None,
    }


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    folder = args[0] if len(args) > 0 else "."
    pattern = args[1] if len(args) > 1 else "*.csv"
    master = args[2] if len(args) > 2 else "master.parquet"
    clean_csv = args[3] if len(args) > 3 else "combined_cleaned.csv"
    out = ingest_folder(folder=folder, pattern=pattern, master_parquet=master, export_clean_csv=clean_csv)
    print(
        f"[bdash_ingest {__BDASH_INGEST_VERSION__}] "
        f"Processed {len(out['files_processed'])} files | rows={out['rows']} | "
        f"deduped={out['deduped_rows']} | Master: {out['master_parquet']} | Clean CSV: {out['clean_csv']}"
    )

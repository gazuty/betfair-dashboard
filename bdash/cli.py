# bdash_cli.py
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import pandas as pd

try:
    from bdash.ingest import ingest_folder
    from bdash.drawdowns import build_risk_artifacts
except ImportError:
    print("Error: bdash_ingest.py or bdash_drawdowns.py not found in repo root.")
    raise

# Import the Google Sheets updater from your existing Results.ipynb logic
try:
    from bdash.sheets import update_google_sheets
except ImportError:
    update_google_sheets = None


def cmd_ingest(args: argparse.Namespace) -> int:
    root = Path(args.root)
    if not root.exists():
        print(f"Error: root folder not found: {root}")
        return 2

    master = Path(args.master).expanduser() if args.master else root / "master.parquet"
    clean_csv = Path(args.clean_csv).expanduser() if args.clean_csv else (root / "combined_cleaned.csv")

    print(f"[bdash_cli] Ingest starting...")
    result = ingest_folder(
        folder=str(root),
        pattern=args.pattern,
        master_parquet=str(master),
        export_clean_csv=str(clean_csv),
    )

    print(f"[bdash_cli] Ingest done: {result['rows']} rows ({result['deduped_rows']} deduped)")
    return 0


def cmd_risk(args: argparse.Namespace) -> int:
    master = Path(args.master).expanduser()
    if not master.exists():
        print(f"Error: master parquet not found: {master}")
        return 2

    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(master)
    print(f"[bdash_cli] Risk build starting...")
    arts = build_risk_artifacts(df=df, out_dir=str(out))

    print("[bdash_cli] Risk build complete.")
    print(json.dumps(arts["stats"], indent=2))
    return 0


def cmd_sheets(args: argparse.Namespace) -> int:
    if update_google_sheets is None:
        print("Error: update_google_sheets not available. Make sure scripts/update_sheets.py exists.")
        return 2

    master = Path(args.master).expanduser()
    if not master.exists():
        print(f"Error: master parquet not found: {master}")
        return 2

    df = pd.read_parquet(master)
    print(f"[bdash_cli] Updating Google Sheet '{args.sheet_name}'...")
    update_google_sheets(df, args.sheet_name)
    print("[bdash_cli] Google Sheet update complete.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bdash_cli", description="Betfair Dashboard CLI")
    sub = p.add_subparsers(dest="command", required=True)

    # ingest
    pi = sub.add_parser("ingest", help="Ingest CSVs -> master.parquet + combined_cleaned.csv")
    pi.add_argument("--root", required=True, help="Folder with raw Betfair CSVs")
    pi.add_argument("--pattern", default="*.csv", help="Glob pattern for CSV files")
    pi.add_argument("--master", default="", help="Output parquet path")
    pi.add_argument("--clean-csv", dest="clean_csv", default="", help="Output cleaned CSV path")
    pi.set_defaults(func=cmd_ingest)

    # risk
    pr = sub.add_parser("risk", help="Build risk artifacts")
    pr.add_argument("--master", required=True, help="Path to master.parquet")
    pr.add_argument("--out", required=True, help="Output folder for artifacts")
    pr.set_defaults(func=cmd_risk)

    # sheets
    ps = sub.add_parser("sheets", help="Push dashboard tables to Google Sheets")
    ps.add_argument("--master", required=True, help="Path to master.parquet")
    ps.add_argument("--sheet-name", required=True, help="Name of target Google Sheet")
    ps.set_defaults(func=cmd_sheets)

    return p


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

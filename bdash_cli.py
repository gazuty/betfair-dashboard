# bdash_cli.py
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

# Local imports (repo root)
try:
    from bdash_ingest import ingest_folder, __BDASH_INGEST_VERSION__
except Exception as e:
    print("Error: could not import bdash_ingest. Make sure bdash_ingest.py is in the repo root.")
    raise

try:
    from bdash_drawdowns import build_risk_artifacts
except Exception as e:
    print("Error: could not import bdash_drawdowns. Make sure bdash_drawdowns.py is in the repo root.")
    raise


def cmd_ingest(args: argparse.Namespace) -> int:
    root = Path(args.root)
    if not root.exists():
        print(f"Error: root folder not found: {root}")
        return 2

    master = Path(args.master).expanduser() if args.master else root / "master.parquet"
    clean_csv = Path(args.clean_csv).expanduser() if args.clean_csv else (root / "combined_cleaned.csv")

    print(f"[bdash_cli] Ingest starting...")
    print(f"  root       : {root}")
    print(f"  master     : {master}")
    print(f"  clean_csv  : {clean_csv}")

    result = ingest_folder(
        folder=str(root),
        pattern=args.pattern,
        master_parquet=str(master),
        export_clean_csv=str(clean_csv),
    )

    print(f"[bdash_cli] Ingest done with bdash_ingest {result['version']}")
    print(f"  files      : {len(result['files_processed'])}")
    print(f"  rows       : {result['rows']}")
    print(f"  deduped    : {result['deduped_rows']}")
    print(f"  master     : {result['master_parquet']}")
    print(f"  clean_csv  : {result['clean_csv']}")
    return 0


def cmd_risk(args: argparse.Namespace) -> int:
    master = Path(args.master).expanduser()
    if not master.exists():
        print(f"Error: master parquet not found: {master}")
        return 2

    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)

    # Load cleaned dataframe from Parquet (faster; preserves dtypes)
    import pandas as pd
    df = pd.read_parquet(master)

    print(f"[bdash_cli] Risk build starting...")
    print(f"  master     : {master}")
    print(f"  out        : {out}")

    arts = build_risk_artifacts(df=df, out_dir=str(out))

    print("[bdash_cli] Risk build complete:")
    print(f"  equity_png      : {arts['equity_png']}")
    print(f"  underwater_png  : {arts['underwater_png']}")
    print(f"  worst_days_csv  : {arts['worst_days_csv']}")
    print(f"  rolling_csv     : {arts['rolling_csv']}")
    print(f"  stats_json      : {arts['stats_json']}")

    # Echo headline stats to stdout for quick CI logs
    print("[bdash_cli] Stats:")
    print(json.dumps(arts["stats"], indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bdash_cli", description="Betfair Dashboard CLI")
    sub = p.add_subparsers(dest="command", required=True)

    # ingest
    pi = sub.add_parser("ingest", help="Ingest CSVs and write master.parquet + combined_cleaned.csv")
    pi.add_argument("--root", required=True, help="Folder with raw Betfair CSVs (e.g., '/content/drive/My Drive/Betfair')")
    pi.add_argument("--pattern", default="*.csv", help="Glob pattern for CSV files (default: *.csv)")
    pi.add_argument("--master", default="", help="Output parquet path (default: <root>/master.parquet)")
    pi.add_argument("--clean-csv", dest="clean_csv", default="", help="Output cleaned CSV path (default: <root>/combined_cleaned.csv)")
    pi.set_defaults(func=cmd_ingest)

    # risk
    pr = sub.add_parser("risk", help="Build risk artifacts (equity, drawdown, worst days, rolling, stats)")
    pr.add_argument("--master", required=True, help="Path to master.parquet")
    pr.add_argument("--out", required=True, help="Output folder for artifacts")
    pr.set_defaults(func=cmd_risk)

    return p


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

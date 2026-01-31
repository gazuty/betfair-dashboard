from __future__ import annotations

import os
from pathlib import Path

import papermill as pm


def load_dotenv_fallback(dotenv_path: Path) -> None:
    """
    Minimal .env loader (only KEY=VALUE lines).
    Used only if python-dotenv isn't installed.
    """
    if not dotenv_path.exists():
        return

    for raw in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)  # do not overwrite existing vars


def load_env(repo_root: Path) -> None:
    dotenv_path = repo_root / ".env"

    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv(dotenv_path=dotenv_path, override=False)
        print(f"✅ Loaded .env via python-dotenv: {dotenv_path}")
    except Exception:
        load_dotenv_fallback(dotenv_path)
        print(f"✅ Loaded .env via fallback parser: {dotenv_path}")


def main() -> int:
    repo_root = Path(__file__).resolve().parent
    os.chdir(repo_root)

    notebook_in = repo_root / "notebooks" / "betfair_dashboard_STABLE.ipynb"
    out_dir = repo_root / "out"
    notebook_out = out_dir / "last_run.ipynb"

    out_dir.mkdir(parents=True, exist_ok=True)

    if not notebook_in.exists():
        print(f"❌ Notebook not found: {notebook_in}")
        return 2

    load_env(repo_root)

    print("🚀 Running Betfair Dashboard (stable) via Papermill")
    print(f"   CWD:      {repo_root}")
    print(f"   INPUT:    {notebook_in}")
    print(f"   OUTPUT:   {notebook_out}")

    # Only pass parameters if present in the environment
    pm_params = {
        k: v
        for k, v in {
            # File paths
            "BASE_FOLDER": os.getenv("BASE_FOLDER"),
            "MASTER_CSV": os.getenv("MASTER_CSV"),
            "GOOGLE_SERVICE_ACCOUNT_JSON": os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"),
            # Google Sheets
            "GOOGLE_SHEET_NAME": os.getenv("GOOGLE_SHEET_NAME"),
            # Analysis settings
            "ROLLING_START_DATE": os.getenv("ROLLING_START_DATE"),
            "WEEK_START_DAY": os.getenv("WEEK_START_DAY"),
            "TOP_N_TRACKS": int(os.getenv("TOP_N_TRACKS")) if os.getenv("TOP_N_TRACKS") else None,
            "TOP_N_STRIKE_RATES": int(os.getenv("TOP_N_STRIKE_RATES")) if os.getenv("TOP_N_STRIKE_RATES") else None,
        }.items()
        if v is not None
    }

    try:
        pm.execute_notebook(
            input_path=str(notebook_in),
            output_path=str(notebook_out),
            parameters=pm_params,
            log_output=True,
        )
    except Exception as e:
        print("\n❌ Papermill run failed.")
        print(f"   Error: {e}")
        print(f"   Partial output (if any): {notebook_out}")
        return 1

    print("\n✅ Done.")
    print(f"📄 Output notebook: {notebook_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

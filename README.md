# 📊 Betfair Dashboard (Stable)

This repository contains a stable notebook pipeline that processes Betfair profit/loss data
and publishes summary tables to Google Sheets.

**Source of truth:** `notebooks/betfair_dashboard_STABLE.ipynb`  
**Local runner:** `run_dashboard.py` (Papermill)  
**Helpers (unit tested):** `dashboard_lib.py`

---

## Quickstart (Local)

### 1. Create & activate a virtual environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
On macOS/Linux: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`.

### 2. Configure
Copy `.env.example` to `.env` and set:

- `BASE_FOLDER`: the folder holding new `BettingPandL*.csv` exports (processed files move to `Archive/` inside it)
- `MASTER_CSV`: the master CSV the exports are merged into
- `GOOGLE_SHEET_NAME`: the target Google Sheet
- `GOOGLE_SERVICE_ACCOUNT_JSON`: path to a Google service-account key. Keep it in `.secrets/`. Share the sheet with the service account's email address.

### 3. Run
```powershell
python run_dashboard.py
```
The executed notebook, with its outputs, is written to `out/last_run.ipynb` (git-ignored).
If the safety check finds the master and the raw exports disagree, the run stops before publishing.

## Development

```powershell
pip install -r requirements-dev.txt
pre-commit install
pytest
```

The pre-commit hook strips notebook outputs. They have held real betting results in the past, and this repository is public. A test also fails if the committed notebook has any outputs.

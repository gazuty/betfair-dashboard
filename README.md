# 📊 Betfair Dashboard (Stable)

This repository contains a stable notebook pipeline that processes Betfair profit/loss data
and publishes summary tables to Google Sheets.

**Source of truth:** `notebooks/betfair_dashboard_STABLE.ipynb`  
**Local runner:** `run_dashboard.py` (Papermill)

---

## Quickstart (Local)

### 1. Create & activate a virtual environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

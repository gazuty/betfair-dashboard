# Betfair Dashboard

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](
https://colab.research.google.com/github/gazuty/betfair-dashboard/blob/colab-stable-2025-08-10/notebooks/betfair_dashboard_STABLE_2025-08-10.ipynb
)

## Project status (2025-08-10)

- **Stable (default):** `colab-stable-2025-08-10`  
  - Notebook: `notebooks/betfair_dashboard_STABLE_2025-08-10.ipynb`
  - Known-good: updates Google Sheets with minimal write calls and a pre-push sanity check.
- **Experimental:** `upgrade-experimental-2025-08-10`  
  - Work in progress; breaking changes expected. Do **not** rely on it for daily updates.

---

## How to run (Colab quickstart)

1. Open the stable notebook: `notebooks/betfair_dashboard_STABLE_2025-08-10.ipynb`.
2. Set paths in **STEP 0** (BASE_FOLDER, etc.).  
   - Place service account key at: `/content/drive/MyDrive/Betfair/<your-key>.json`  
   - Share the target Google Sheet with that service-account email (Editor).
3. Run **STEP 1 → STEP 7**.
4. Run **STEP 7.5 (Sanity Check)**. It compares yesterday/today totals in `df` vs current RAW files.  
   - If it fails, fix uploads and rerun before pushing.
5. Run **STEP 8 (Export to Sheets)**. Uses one bulk update per sheet (avoids 429).

> Tip: Daily workflow is upload new `BettingPandL*.csv` → run STEPs 1–7 → sanity check → STEP 8.

---

## Safety

- Credentials: **never** commit JSON keys. Use Drive + service account sharing only.
- Backups: the notebook makes timestamped backups of master files before mutations.
- Drive: keep “Version history” on; restore if needed.




## Legacy CLI (optional)

If you still use the older `bdash` CLI locally:

- Install (editable):  
  `pip install -e .`

- Ingest:  
  `bdash ingest --root "/path/to/Betfair"`

- Risk:  
  `bdash risk --master "/path/to/Betfair/master.parquet" --out "/path/to/Betfair/artifacts"`

- Sheets (service account):  
  Share your Google Sheet with the service-account email.  
  `export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json`  
  `bdash sheets --master "/path/to/Betfair/master.parquet" --sheet-name "Betfair Dashboard"`

> The CLI is considered experimental now. Daily runs should use the **stable Colab notebook** documented above.

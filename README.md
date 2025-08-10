# Betfair Dashboard

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




# 🧠 Betfair Dashboard

This project is a personal analytics pipeline for historical betting data from Betfair.

---

## 📁 Repository Structure

- `Results.ipynb`: Main Colab notebook to process Betfair exports and generate summaries
- `scripts/dashboard_charts.gs`: Google Apps Script to generate dashboard charts (optional)
- `Betfair_Master.csv`: Master historical dataset (auto-updated)
- `combined_cleaned.csv`: Archived snapshot of cleaned data

---

## ⚙️ Features

- Loads and deduplicates raw Betfair CSVs
- Archives processed files to `/Archive`
- Extracts Sport, Track, Country, and Event features
- Generates summaries:
  - Daily and cumulative profit/loss
  - Weekly (Sun–Sat) and Monthly summaries
  - Rolling 2, 4, 8 week summaries (from 1 March)
  - Performance by sport and country
  - Daily and rolling summaries for Horse Racing and Greyhounds
  - Top/bottom tracks and strike rates
- Pushes all tables to a Google Sheet titled **Betfair Dashboard**
- Generates a KPI summary in a `Dashboard` tab

---

## 📓 How to Use

1. Download your Betfair "Betting Profit and Loss" CSV files
2. Upload them to your Google Drive under `/My Drive/Betfair/`
3. Open `Results.ipynb` in Google Colab
4. Run all cells to:
   - Update the master dataset
   - Build summary tables
   - Export results to the Google Sheet

Your target Google Sheet **must be titled exactly:**  
`Betfair Dashboard`

---

## 📊 Add Dashboard Charts (Optional)

To automatically generate charts in the `Dashboard` tab:

### 🛠 Step-by-Step Instructions

1. Open your **Google Sheet**: **Betfair Dashboard**
2. Go to `Extensions > Apps Script`
3. Delete any default code and paste in the contents of:  
   [`scripts/dashboard_charts.gs`](./scripts/dashboard_charts.gs)
4. Save the Apps Script project (e.g. `DashboardChartBuilder`)
5. Reload your sheet — a new menu will appear:  
   **📊 Dashboard > Refresh Charts**
6. Click **Refresh Charts** to add:
   - Profit/Loss by day, week, and month
   - Cumulative performance
   - Rolling 2, 4, 8 week summaries (with legend)
   - Horse and Greyhound P/L and rolling
   - Top/bottom tracks and strike rates

> ⚠️ If prompted, authorize the script to access your sheet.

---

### 👨‍💻 Author

**Built by Gazuty (c) 2025**

## Quickstart

### Google Colab
1. Clone & install:
   !git clone https://github.com/gazuty/betfair-dashboard.git
   %pip install -q -e betfair-dashboard

2. Mount Google Drive for data:
   from google.colab import drive
   drive.mount('/content/drive')

3. Run pipeline:
   ROOT = "/content/drive/My Drive/Betfair"
   MASTER = f"{ROOT}/master.parquet"
   ARTS = f"{ROOT}/artifacts"
   !bdash ingest --root "$ROOT"
   !bdash risk --master "$MASTER" --out "$ARTS"

4. Optional: Push to Google Sheets (requires auth).
   bdash sheets --master "$MASTER" --sheet-name "Betfair Dashboard"

### Local
git clone https://github.com/gazuty/betfair-dashboard.git
cd betfair-dashboard
pip install -e .
bdash ingest --root "/path/to/Betfair"
bdash risk --master "/path/to/Betfair/master.parquet" --out "./artifacts"
bdash sheets --master "/path/to/Betfair/master.parquet" --sheet-name "Betfair Dashboard"

### Google Sheets Auth
- Recommended: Service account
- Share target sheet with service account email
- Set GOOGLE_APPLICATION_CREDENTIALS to your JSON key path before running sheets command

---

## Package layout
betfair-dashboard/
  bdash/
    __init__.py
    ingest.py
    drawdowns.py
    sheets.py
    cli.py
  notebooks/Results.ipynb
  scripts/dashboard_charts.gs
  artifacts/ (ignored)
  pyproject.toml
  requirements.txt
  .gitignore

## Commands
- bdash ingest --root <folder>
- bdash risk --master <parquet> --out <folder>
- bdash sheets --master <parquet> --sheet-name "<Sheet Name>"
## Quickstart

### Google Colab
!git clone https://github.com/gazuty/betfair-dashboard.git
%pip install -q -e betfair-dashboard

from google.colab import drive
drive.mount('/content/drive')

ROOT = "/content/drive/My Drive/Betfair"
MASTER = f"{ROOT}/master.parquet"
ARTS = f"{ROOT}/artifacts"

!bdash ingest --root "$ROOT"
!bdash risk --master "$MASTER" --out "$ARTS"

# Optional Google Sheets update
!bdash sheets --master "$MASTER" --sheet-name "Betfair Dashboard"

---

## Package layout
betfair-dashboard/
├─ bdash/
│  ├─ __init__.py
│  ├─ ingest.py
│  ├─ drawdowns.py
│  ├─ sheets.py
│  └─ cli.py
├─ notebooks/
│  └─ Results.ipynb
├─ scripts/
│  └─ dashboard_charts.gs
├─ artifacts/
├─ pyproject.toml
├─ requirements.txt
└─ .gitignore

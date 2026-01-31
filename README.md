# Betfair Results Dashboard

A Python notebook pipeline that processes Betfair profit/loss exports, generates analytics summaries, and publishes results to Google Sheets.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/gazuty/betfair-dashboard/blob/colab-stable-2025-08-10/notebooks/betfair_dashboard_STABLE.ipynb)

## Features

- **Automated data ingestion** — Reads Betfair P&L CSV exports and merges into a master dataset
- **Smart deduplication** — Uses hash-based comparison to avoid duplicate entries
- **Multi-dimensional summaries** — Daily, weekly, monthly, by sport, by country, and by track
- **Rolling returns** — 2-week, 4-week, and 8-week rolling profit calculations
- **Strike rate analysis** — Win rate tracking per track with configurable thresholds
- **Google Sheets export** — Publishes 30+ summary tables to a Google Sheet dashboard
- **Colab & local support** — Works in Google Colab or local Jupyter with Papermill

## Requirements

- Python 3.8+
- Google Cloud service account with Google Sheets API enabled
- Google Colab (recommended) or local Jupyter environment

## Installation

### Option 1: Google Colab (Recommended)

1. Click the "Open in Colab" badge above
2. Upload your service account JSON to Google Drive (e.g., `My Drive/.secrets/google_service_account.json`)
3. Update the `GOOGLE_SERVICE_ACCOUNT_JSON` path in the Parameters cell
4. Run all cells: **Runtime → Run all**

### Option 2: Local Jupyter / Papermill

```bash
# Clone the repository
git clone https://github.com/gazuty/betfair-dashboard.git
cd betfair-dashboard

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or: .\.venv\Scripts\Activate.ps1  # Windows PowerShell

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your paths

# Run via Papermill
python run_dashboard.py
```

## Configuration

All settings are in the **Parameters** cell at the top of the notebook. These can be overridden via environment variables or Papermill parameters.

### File Paths

| Parameter | Description | Default |
|-----------|-------------|---------|
| `BASE_FOLDER` | Root folder containing P&L exports and Archive | `data` |
| `MASTER_CSV` | Path to the consolidated master CSV file | `data/Betfair_Master.csv` |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Path to Google service account credentials | `.secrets/google_service_account.json` |

### Google Sheets

| Parameter | Description | Default |
|-----------|-------------|---------|
| `GOOGLE_SHEET_NAME` | Name of the target Google Sheet | `Betfair Dashboard` |

### Analysis Settings

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ROLLING_START_DATE` | Start date for rolling return calculations | `2025-03-01` |
| `WEEK_START_DAY` | Day to start weekly aggregations (pandas resample format) | `W-SUN` |
| `TOP_N_TRACKS` | Number of top/bottom tracks to include in summaries | `15` |
| `TOP_N_STRIKE_RATES` | Number of top/bottom strike rates to include | `10` |

### Business Rules

| Parameter | Description | Default |
|-----------|-------------|---------|
| `VALID_SPORTS` | Sports to include in track analysis | `['Horse Racing', 'Greyhound Racing']` |
| `MIN_STRIKE_BETS` | Minimum bets required for strike rate calculation | `50` |

## Usage

### Step 1: Prepare Your Data

Export your Betfair P&L data as CSV files with the naming pattern `BettingPandL*.csv` and place them in your `BASE_FOLDER`.

Required columns:
- `Market` — The market description (e.g., "Horse Racing / Ascot 15th Jun : 2:30 Race")
- `Settled date` — When the bet settled
- A profit column (e.g., `Profit/Loss (AUD)` or similar)

### Step 2: Run the Notebook

**In Colab:** Runtime → Run all

**Locally:** `python run_dashboard.py`

The notebook will:
1. Load any new P&L files and merge into the master CSV
2. Archive processed files to `BASE_FOLDER/Archive/`
3. Extract features (sport, track, country) from market names
4. Build summary tables
5. Export everything to Google Sheets

### Step 3: View Results

Open your Google Sheet to see the dashboard with all summary tables.

## Output

The notebook exports 30+ sheets to Google Sheets:

### Core Summaries
| Sheet | Description |
|-------|-------------|
| `Dashboard` | KPIs: total profit, bet count, best/worst days |
| `By Day` | Daily profit with cumulative totals |
| `By Day Sorted` | Daily profit sorted by P&L (best days first) |
| `By Week` | Weekly aggregated profit |
| `By Month` | Monthly aggregated profit |
| `By Sport` | Total profit per sport |
| `By Country` | Total profit per country |
| `Cumulative` | Cumulative profit over time |

### Rolling Returns
| Sheet | Description |
|-------|-------------|
| `Rolling Returns` | Overall 2w/4w/8w rolling profit |
| `Rolling Horse Racing` | Rolling returns for horse racing |
| `Rolling Greyhound Racing` | Rolling returns for greyhound racing |

### Track Analysis
| Sheet | Description |
|-------|-------------|
| `Track Stats` | All tracks with total P&L |
| `Top Horse Tracks` | Best performing horse racing tracks |
| `Bottom Horse Tracks` | Worst performing horse racing tracks |
| `Top Greyhound Tracks` | Best performing greyhound tracks |
| `Bottom Greyhound Tracks` | Worst performing greyhound tracks |

### Strike Rates
| Sheet | Description |
|-------|-------------|
| `Top Strike Rates` | Tracks with highest win rates |
| `Bottom Strike Rates` | Tracks with lowest win rates |

### Per-Sport Daily
| Sheet | Description |
|-------|-------------|
| `{Sport} Daily` | Daily profit for each sport (e.g., "Horse Racing Daily") |

## Project Structure

```
betfair-dashboard/
├── notebooks/
│   └── betfair_dashboard_STABLE.ipynb  # Main notebook
├── scripts/
│   └── dashboard_charts.gs             # Google Apps Script for charts
├── .env.example                         # Environment variable template
├── .gitignore                           # Git ignore patterns
├── CONTRIBUTING.md                      # Contribution guidelines
├── LICENSE                              # MIT License
├── README.md                            # This file
├── requirements.txt                     # Python dependencies
└── run_dashboard.py                     # Local Papermill runner
```

## Troubleshooting

### Service Account Authentication Errors

```
FileNotFoundError: Service account JSON not found
```

**Solution:** Ensure your service account JSON file exists at the path specified in `GOOGLE_SERVICE_ACCOUNT_JSON`. Download it from Google Cloud Console → IAM & Admin → Service Accounts.

### Missing Columns in Betfair Exports

```
⚠️ {filename} missing columns: {'Market', 'Settled date'}
```

**Solution:** Ensure your Betfair export includes the required columns. The notebook looks for:
- `Market` (exact name)
- `Settled date` (exact name)
- Any column containing "profit" (case-insensitive)

### Google Sheets API Rate Limits

```
⏳ Rate limited; retrying in 3s...
```

**Solution:** This is normal — the notebook automatically retries with exponential backoff. If it persists, wait a few minutes before running again.

### Cell Execution Order Errors

```
RuntimeError: ⚠️ Run STEP 0 (Configuration & Utilities) first
```

**Solution:** Run all cells in order using **Runtime → Run all**. Each step depends on variables from previous steps.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License — see [LICENSE](LICENSE) for details.

---

Built by [gazuty](https://github.com/gazuty) © 2025

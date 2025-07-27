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
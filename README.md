# 🧠 Betfair Dashboard

This project is a personal analytics pipeline for historical betting data from Betfair.

## 📁 Repository Structure

- `Results.ipynb`: Main Colab notebook to process Betfair exports and generate summaries.
- `scripts/dashboard_charts.gs`: Google Apps Script to generate dashboard charts (optional).
- `combined_cleaned.csv`: Archived cleaned dataset (auto-generated).
- `Betfair_Master.csv`: Master historical dataset.

## ⚙️ Features

- Loads raw Betfair CSV exports
- Deduplicates and cleans data
- Extracts features like Sport, Track, Country
- Generates daily, weekly, and monthly summaries
- Calculates top/bottom performing tracks and strike rates
- Updates a Google Sheet with key outputs
- Builds a summary dashboard tab with KPIs

## 📓 How to Use

1. Download your Betfair "Betting Profit and Loss" CSVs
2. Upload them to your Google Drive under `/My Drive/Betfair/`
3. Open `Results.ipynb` in Google Colab and run the notebook
4. The cleaned data will be pushed to your Google Sheet titled **Betfair Dashboard**

---

### 📊 Adding the Dashboard Charts (Optional)

If you'd like to automatically insert charts into the `Dashboard` tab in your Google Sheet:

#### 🔧 Step-by-Step Instructions

1. Open your **Google Sheet** named **Betfair Dashboard**  
   (this is the one your Colab notebook pushes results to)

2. Go to **Extensions > Apps Script**

3. Delete any default code and paste in the contents of  
   [`scripts/dashboard_charts.gs`](./scripts/dashboard_charts.gs) from this repo

4. Save the project with any name (e.g., `DashboardChartBuilder`)

5. Close the Apps Script editor

6. Back in your sheet, refresh the page. You will see a new menu:  
   **📊 Dashboard > Refresh Charts**

7. Click **Refresh Charts** to automatically insert visual summaries including:
   - Profit/Loss by day, week, and month
   - Cumulative performance
   - Sport breakdowns
   - Top/bottom horse tracks
   - Strike rates

> ⚠️ If prompted for authorization the first time, grant permission to run the script.
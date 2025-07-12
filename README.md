# Betfair Dashboard Automation

This project provides a fully automated pipeline to process Betfair Profit & Loss exports and visualize them using Google Looker Studio. It supports daily, weekly, and monthly summaries, strike rate analysis, and per-track profitability insights.

---

## 🚀 Features

- **Master Data Management**: Incrementally builds a master dataset from exported `BettingPandL` CSVs.
- **Automatic Archiving**: Processed CSVs are archived to prevent duplication.
- **Feature Extraction**: Extracts `Sport`, `Track_Name`, `Country`, and event descriptions.
- **Daily, Weekly, Monthly Reporting**: Summarizes performance over various time windows.
- **Sport-specific Trends**: Generates individual tables for each sport (e.g., Horse Racing Daily).
- **Track Performance Analysis**: Identifies top/bottom tracks by profit and strike rate.
- **Strike Rate Computation**: Tracks performance across tracks with minimum bet thresholds.
- **Google Sheets Export**: All reports sync to a Google Sheet for Looker Studio integration.
- **Looker Studio Template**: Comes with a sharable dashboard template.

---

## 📂 Folder Structure

```
/My Drive/Betfair/
├── BettingPandL*.csv          ← Export files from Betfair
├── Results Summary export ... ← Optional results file
├── Betfair_Master.csv         ← Auto-generated master file
├── Archive/                   ← Auto-archived processed files
```

---

## ✅ Setup Steps

### 1. Clone the Repo in Google Colab

Open Colab and clone your GitHub repo, or copy the notebook script provided.

### 2. Mount Google Drive

```python
from google.colab import drive
drive.mount('/content/drive')
```

### 3. Set Configuration

Ensure the folder structure and config in the script match your Google Drive paths.

```python
BASE_FOLDER = '/content/drive/My Drive/Betfair'
```

### 4. Connect to Google Sheets

Use `gspread` and `gspread_dataframe` to authenticate and connect to a sheet called **Betfair Dashboard**.

### 5. Run the Pipeline

Each step of the notebook processes data and syncs the results to your Google Sheet.

---

## 📊 Dashboard

Use [this Looker Studio Template](https://lookerstudio.google.com/s/vYrmf16mdp8) and connect it to your own Google Sheet (named `Betfair Dashboard`) to view:

- KPIs (Total Profit, Best/Worst Day)
- Daily/Weekly/Monthly charts
- Top/Bottom Track Performance
- Strike Rate summaries
- Per-Sport Daily Trends

---

## 🧠 Business Logic

- **Profit Column Detection**: Automatically detects `Profit_Loss` from columns with "profit" or "AUD".
- **Country Parsing**: Defaults to `UK` if no country is listed for racing sports.
- **Strike Rate Filter**: Only tracks with ≥50 bets are shown in the summary.
- **Duplicates**: Uses a composite key to avoid importing duplicates to the master.

---

## 🛠 Requirements

- Google Colab
- Google Drive access
- Google Sheets API access (`gspread`)
- pandas

---

## 📌 Tips

- Keep consistent column names in your exports.
- Always review your `Betfair_Master.csv` before rerunning.
- Archive or rename processed `BettingPandL` files to avoid duplication.

---

## 🤝 Contributing

Contributions welcome! Fork this repo and submit a pull request with improvements or bug fixes.

---

## 📄 License

MIT License — free to use, modify, and distribute.
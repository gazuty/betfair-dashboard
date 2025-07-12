# 📈 Betfair Dashboard Automation

This project builds a fully automated dashboard in Google Sheets for analysing Betfair profit/loss performance over time, by sport, by track, and more.

It processes Betfair export files (`BettingPandL*.csv`), maintains a master dataset, calculates rich summaries, and syncs them to a Google Sheet dashboard with one click.

---

## 🚀 Features

- ✅ Appends raw P&L files to a master dataset, skipping duplicates
- ✅ Extracts sport, track, country and event information
- ✅ Tracks daily, weekly, monthly, and cumulative profit/loss
- ✅ Produces summaries by sport, country, and individual tracks
- ✅ Identifies top and bottom performing tracks
- ✅ Calculates strike rates per track (with filter for minimum bets)
- ✅ Outputs 28+ fully formatted Google Sheets tabs
- ✅ Creates a dynamic KPI dashboard (total profit, best/worst day)

---

## 📁 Folder Structure

Your Google Drive should include:

```
/My Drive/
├── Betfair/
│   ├── BettingPandL_*.csv         # Raw P&L files from Betfair
│   ├── Betfair_Master.csv         # Master dataset (auto-managed)
│   ├── Archive/                   # Processed CSVs (auto-archived)
```

---

## ✅ Setup Instructions (Google Colab)

1. Open the notebook from GitHub:

   [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/gazuty/betfair-dashboard/blob/main/Results.ipynb)

2. Follow the notebook cell-by-cell:
   - Mount your Google Drive
   - Set your folder paths (adjust only if needed)
   - Run each step from master update ➝ analysis ➝ Google Sheets export

3. Authorize access when prompted (Google Sheets & Drive)

4. The first time you run it, create a blank Google Sheet titled:  
   `Betfair Dashboard`

---

## 📊 Output

The notebook automatically updates tabs in your Google Sheet, including:

### 📌 Core Tabs:
- **By Day**
- **By Week**
- **By Month**
- **By Sport**
- **By Country**
- **Cumulative**

### 🏇 Track Analysis:
- **Track Stats**
- **Top/Bottom Horse Tracks**
- **Top/Bottom Greyhound Tracks**
- **Top/Bottom Strike Rates**

### 🎯 Sport-Specific:
- **Horse Racing Daily**
- **Greyhound Racing Daily**
- *(plus all other sports encountered)*

### 📋 Dashboard KPIs:
- Total Profit/Loss  
- Number of Bets  
- Best & Worst Day  
- Report Generated Date

---

## ⚙️ Configuration

Modify the first cell to adjust folder paths, sheet name, and business rules:

```python
BASE_FOLDER       = '/content/drive/My Drive/Betfair'
GOOGLE_SHEET_NAME = 'Betfair Dashboard'
VALID_SPORTS      = ['Horse Racing', 'Greyhound Racing']
MIN_STRIKE_BETS   = 50
```

---

## 🔄 Automation Tip

To run this on a schedule, you can trigger the notebook via Google Colab Pro+ or integrate with [Pipedream](https://pipedream.com/) or [Make.com](https://www.make.com/) + Colab APIs.

---

## 🧠 Author

Created and maintained by [@gazuty](https://github.com/gazuty)  
Enhancements and refactoring by OpenAI's ChatGPT (assistant)

---

## 📜 License

MIT License — use freely, improve openly!
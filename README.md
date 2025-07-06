
# Betfair Dashboard

This project analyzes Betfair profit/loss data using Python in Google Colab and visualizes it in Google Sheets.  
It automates:
- Merging and deduping data files
- Building summaries (by day, week, month, sport, country)
- Track and strike rate analysis (Horse Racing, Greyhound Racing)
- Exporting to Google Sheets for charting with Apps Script

---

## 📁 Repository Structure
```
notebooks/                  # Your Colab notebooks
apps_script/                 # Apps Script for Google Sheets charts
.gitignore                   # Files to exclude from git (e.g. raw data)
README.md                    # This file
```

---

## 🚀 How to Use

### 1️⃣ **Update and Run the Notebook**
- Open the notebook in [Google Colab](https://colab.research.google.com/)
- Adjust file paths if needed:  
  Example in code:
  ```
  BASE_FOLDER = '/content/drive/My Drive/Betfair'
  ```
  ➡ Change this if your files are stored in a different folder in Google Drive.

- Run the cells in order:
  - **STEP 1:** Loads master CSV, merges new files, dedupes, and updates master  
  - **STEP 2:** Loads the updated master file  
  - **STEP 3:** Extracts sport, track, and country info  
  - **STEP 4:** Builds summaries: day, week, month, sport, country  
  - **STEP 6:** Builds track summaries  
  - **STEP 7:** Computes strike rates  
  - **STEP 8:** Prepares data for export  
  - **STEP 9:** Exports to Google Sheets  

### 2️⃣ **Adjust Google Sheets settings**
- Ensure your Google Sheets file is created and named correctly (default is `"Betfair Dashboard"`)
- In the export code, change the name if needed:
  ```
  GOOGLE_SHEET_NAME = 'Betfair Dashboard'
  ```

### 3️⃣ **Use the Apps Script**
- Paste `apps_script/dashboard_charts.js` into your Google Sheets Apps Script editor
- Run `Refresh Charts` from the menu to build/update charts
- The script formats columns and generates charts dynamically

---

## ⚠ Important Notes
- **File paths:** All file paths assume Google Drive mounted at `/content/drive/`. Adjust `BASE_FOLDER` if your setup differs.
- **Data files:** This repo does not store raw data (CSV/XLSX) — keep those private.
- **Sensitive data:** Ensure you do not commit real data files to GitHub. Use `.gitignore` to prevent this.
- **Chart columns:** The Apps Script assumes certain column positions (e.g. B = label, C = numeric). Adjust `chartConfigs` in the script if your data layout changes.

---

## 📌 Example adjustments
If you store data elsewhere in Drive:
```
BASE_FOLDER = '/content/drive/My Drive/BetfairData'
```
If your Google Sheet is named differently:
```
GOOGLE_SHEET_NAME = 'MyBetfairDashboard'
```

---

## 🛠 Dependencies
- Python (pandas, gspread, gspread_dataframe, oauth2client)
- Google Colab
- Google Drive
- Google Sheets + Apps Script

---

## ✅ Tips
- Run the full pipeline before exporting to Google Sheets for clean data
- Regularly commit updated notebooks to GitHub to track your changes
- Use GitHub Issues to note improvements or bugs

---

## 📌 License
This project is for personal or educational use. You can adapt it freely for your needs.

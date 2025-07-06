
# Betfair Dashboard

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/gazuty/betfair-dashboard/blob/main/Results.ipynb)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

This project analyzes Betfair profit/loss data using Python in Google Colab and visualizes it in Google Sheets.

It is designed to be **beginner-friendly**, with clear steps, while also being easy for **more experienced coders** to follow, review, and contribute to.

The code prioritizes readability, transparency, and clear structure for learning and collaboration.

---

## 📁 Repository Structure
```
Results.ipynb                # Main notebook for data processing
apps_script/                  # Google Sheets Apps Script code for charts
.gitignore                    # Files to exclude from git
README.md                     # This file
LICENSE                       # License file
```

---

## 🚀 How to Use

### 1️⃣ Update and Run the Notebook
- Open the notebook in [Google Colab](https://colab.research.google.com/github/gazuty/betfair-dashboard/blob/main/Results.ipynb)
- Adjust file paths if needed:
  ```python
  BASE_FOLDER = '/content/drive/My Drive/Betfair'
  ```
- Run the cells in order:
  - STEP 1: Update master CSV, merge new files
  - STEP 2: Load master data
  - STEP 3: Extract sport, track, country
  - STEP 4: Build summaries (day, week, month, sport, country)
  - STEP 6: Track summaries
  - STEP 7: Strike rates
  - STEP 8: Prepare export tables
  - STEP 9: Export to Google Sheets

### 2️⃣ Use the Apps Script
- Paste your Apps Script into Google Sheets
- Use the custom menu to refresh charts

---

## 📌 Beginner Tips
- Each cell is labeled and documented for clarity
- You can run the notebook top-to-bottom without advanced Python knowledge
- You can stop after any step — it’s modular

---

## ⚠ Important Notes
- File paths assume Google Drive mounted at `/content/drive/`
- This repo does not store raw data (CSV/XLSX)
- Use `.gitignore` to prevent committing data files

---

## 🛠 Dependencies
- Python: pandas, gspread, gspread_dataframe, oauth2client
- Google Colab + Drive + Sheets + Apps Script

---

## 🙌 Contributing and Feedback
This project welcomes ideas, improvements, and feedback.  
Feel free to fork, open issues, or suggest changes via pull requests.

---

## 📌 License
This project is licensed under the MIT License — see the LICENSE file for details.

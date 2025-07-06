
# Betfair Dashboard

A Google Colab + Google Sheets project for processing, analyzing, and visualizing Betfair results data.  
Designed to be beginner-friendly while offering structure and clarity for more experienced coders.

## 🚀 Getting Started

If you’re starting fresh:  
📝 Simply place your **raw Betfair results CSV files** into the Google Drive folder you are using for this project.  
The system will automatically:
- Load your raw files
- Create a master consolidated CSV (`Betfair_Master.csv`)
- Archive the raw files to keep things tidy

➡ **No existing master file is needed — the code will create one for you!**

## 🛠 Requirements

To run this project you will need:

✅ A **Google account**  
✅ Access to **Google Drive**  
✅ Google Colab (free, runs in browser — part of Google ecosystem)  
✅ Your Google Drive path where you will store:
- Your raw Betfair results CSV files
- The generated master file (`Betfair_Master.csv`)

📝 *Tip:* The code examples in this project assume a folder path like:  
```
/content/drive/My Drive/Betfair
```
You can change this path in the code if your folder is different.

## 📂 Repository Contents

- `Results.ipynb` — main notebook containing the code to process and export data  
- `Apps Script` — builds charts in Google Sheets  
- `CONTRIBUTING.md` — guide for contributors  
- `LICENSE` — MIT License  
- Example outputs (optional: add screenshots here!)

## 🤝 Contributing

This project was originally created by **gazuty** — contributions are welcome to help it grow!

See [CONTRIBUTING.md](./CONTRIBUTING.md) for how to get started.

## 📄 License

This project is licensed under the MIT License.

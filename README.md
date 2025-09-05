# 📜 D&D Campaign Tracker (Streamlit)

An easy, shareable tracker for your D&D (or any TTRPG) campaign—built with **Python + Streamlit**.  
Track player levels, last-session notes, quest hooks, loot, and more. Share a **read-only link** with your players.

---

## ✨ Features
- Add/edit/delete rows (GM view)
- Read-only **public mode** via `?mode=public`
- Search + sort
- Fields: Player, Character, Level, XP, Session Date, Location, What Happened Last, Quest Hooks, Loot/Rewards
- Export to CSV
- **Persistence options:**
  - **Google Sheets** (recommended for sharing + durability)
  - CSV fallback (good for local testing)

---

## 🚀 Quick Start (Local)

1) Create and activate a virtual environment (optional but recommended)
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

2) Install requirements
```bash
pip install -r requirements.txt
```

3) Run
```bash
streamlit run app.py
```

The app opens in your browser at `http://localhost:8501`.

> In local CSV mode, data is saved to `campaign_tracker.csv` in the project folder.

---

## ☁️ Deploy & Share (Streamlit Community Cloud)

1) Push these files to a **public GitHub repo**.
2) Go to **https://streamlit.io/cloud** and deploy the repo.
3) (Optional but recommended) Set up **Google Sheets** persistence (below).
4) Share your app URL with your players.
   - For a read-only view, add `?mode=public` to the end of the URL.

Example:  
`https://your-app.streamlit.app/?mode=public`

---

## 🟢 Google Sheets Persistence (Recommended)

This lets your app save/load from a Google Sheet (great for multiple editors + long-term storage).

### Step A — Create a Service Account
1. Visit **https://console.cloud.google.com/** (create a project if needed).
2. Enable **Google Drive API** and **Google Sheets API** for the project.
3. Create a **Service Account** (IAM & Admin → Service Accounts).
4. Create a **JSON key** for the Service Account and download it.

### Step B — Create a Sheet & Share It
1. Create a new Google Sheet (or use an existing one). Name it anything (e.g., `DnD Tracker`).  
2. **Share** the sheet with your service account’s email (ends with `@<project>.iam.gserviceaccount.com`) and give **Editor** access.
3. Copy the **Sheet URL** (or note the exact name).

### Step C — Add Environment Variables (in Streamlit Cloud)
In your app’s **Settings → Secrets**, add:

- `GSHEETS_SA_JSON` : Paste the entire contents of your service account JSON file.
- `GSHEETS_SHEET_NAME` : Paste the **full URL** of your Google Sheet (recommended), _or_ the exact name.

Click **Save** and **Reboot** the app.

That’s it. The app will auto-detect Google Sheets. If anything fails, it will fall back to CSV and show a warning.

---

## 🔒 GM vs. Player Views

- **GM view (edit mode):** default mode (no query param) lets you add/edit/delete rows.
- **Player view (read-only):** share the link with `?mode=public` to hide all edit controls.

---

## 🧩 Customize Columns

Edit `DEFAULT_COLUMNS` in `app.py` to add/remove fields.  
New columns will automatically appear in the grid/editor.

---

## 🛠️ Troubleshooting

- **Google Sheets: PERMISSION DENIED**  
  Ensure the Sheet is shared with your **Service Account** email, with **Editor** access.
- **Data not saving on Streamlit Cloud without Sheets**  
  The app's filesystem may reset on redeploy; use Google Sheets for reliable persistence.
- **Emoji/Icons not showing**  
  Some terminal fonts don't show emojis; the app still works fine.

---

## 💡 Ideas to Extend
- Add per-character pages
- Session logs with markdown notes
- Upload handouts/images (Streamlit `file_uploader`)
- Simple authentication (e.g., a shared "edit key" in secrets)
- Separate tabs for party vs. NPCs

---

**Made with ❤️ in Python.** Happy adventuring!

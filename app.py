import os
import json
import csv
from io import StringIO
from typing import Dict

import requests
import streamlit as st

# -----------------------------
# App Settings
# -----------------------------
st.set_page_config(page_title="D&D Party Tracker", page_icon="☀️", layout="wide")

# ---- Background image (URL) ----
BACKGROUND_URL = "https://i.pinimg.com/1200x/da/e2/ab/dae2ab85ba612195ad5f49ba2dc8138e.jpg"  # <-- change me

st.markdown(f"""
<style>
/* App background */
.stApp {{
  background: url('{BACKGROUND_URL}') no-repeat center center fixed;
  background-size: cover;
}}
/* Make the main content readable on top of the image */
.block-container {{
  background: rgba(255,255,255,0.88);
  border-radius: 18px;
  padding: 1.5rem 2rem;
}}
/* Sidebar background */
[data-testid="stSidebar"] > div:first-child {{
  background: rgba(255,255,255,0.9);
}}
</style>
""", unsafe_allow_html=True)

# --- glassy panels & badges ---
st.markdown("""
<style>
:root{
  --panel-alpha: 0.45;      /* transparency (0=transparent, 1=solid) */
  --panel-bg: 255,255,255;  /* white glass; use 17,24,39 for dark glass */
  --panel-text: #111827;    /* text color for white glass */
}

/* main page container */
.block-container{
  background: rgba(var(--panel-bg), var(--panel-alpha));
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  border-radius: 18px;
  padding: 1.5rem 2rem;
}

/* sidebar panel */
[data-testid="stSidebar"] > div:first-child{
  background: rgba(var(--panel-bg), calc(var(--panel-alpha) + 0.06));
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  border-right: 1px solid rgba(255,255,255,0.25);
}

/* card container */
.card{
  background: rgba(var(--panel-bg), var(--panel-alpha));
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  border: 1px solid rgba(255,255,255,0.35);
  border-radius: 16px;
  padding: 1rem;
  margin-bottom: 1rem;
}

/* titles above badges */
.badge-title{
  font-size: 1.1rem;
  font-weight: 600;
  letter-spacing: .02em;
  margin-bottom: 0.5rem;
  color: var(--panel-text, #111827);
  opacity: .9;
}

/* circular badge (level) */
.circle-badge{
  width: 80px;
  height: 80px;
  border-radius: 9999px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1.4rem;
  background: rgba(var(--panel-bg), var(--panel-alpha));
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  border: 1px solid rgba(255,255,255,0.35);
  color: var(--panel-text, #111827);
  box-shadow: 0 4px 14px rgba(0,0,0,.08) inset;
}

/* pill badge (date, location) */
.pill-badge{
  display: inline-block;
  padding: 8px 14px;
  border-radius: 9999px;
  font-weight: 700;
  font-size: 1.4rem;
  background: rgba(var(--panel-bg), var(--panel-alpha));
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  border: 1px solid rgba(255,255,255,0.35);
  color: var(--panel-text, #111827);
  line-height: 1.2;
  box-shadow: 0 2px 10px rgba(0,0,0,.06) inset;
}

/* add spacing below badges only on mobile */
@media (max-width: 768px) {
  .circle-badge,
  .pill-badge {
    margin-bottom: 1.5rem;  /* space between stacked badges and next title */
  }
}


/* muted helper text */
.muted{
  color:#6b7280; 
  font-style: italic;
}

/* Force section headings & markdown text to dark */
h1, h2, h3, h4, h5, h6,
.block-container p,
.block-container span,
.block-container div {
  color: var(--panel-text, #111827) !important;
}

</style>
""", unsafe_allow_html=True)

# -----------------------------
# Data model (single party record)
# -----------------------------
PARTY_FIELDS = [
    "Level",
    "Session Date",
    "Location",
    "What Happened Last",
    "Quest Hooks",
    "Loot/Rewards",
]

CSV_FALLBACK_PATH = "party_state.csv"

# -----------------------------
# Backends: Gist (primary), Google Sheets (optional), Local CSV (fallback)
# -----------------------------
def use_gist() -> bool:
    s = st.secrets
    return bool(s.get("GIST_TOKEN", "")) and bool(s.get("GIST_ID", "")) and bool(s.get("GIST_FILENAME", ""))

def _gist_headers() -> dict:
    return {
        "Authorization": f"token {st.secrets['GIST_TOKEN']}",
        "Accept": "application/vnd.github+json",
    }

def _gist_get_raw_url(gist_json: dict, filename: str) -> str:
    files = gist_json.get("files", {})
    if filename in files and "raw_url" in files[filename]:
        return files[filename]["raw_url"]
    return ""

def _gist_read_file() -> str:
    """Return CSV text from the gist, or empty string."""
    gist_id = st.secrets["GIST_ID"]
    filename = st.secrets["GIST_FILENAME"]
    r = requests.get(f"https://api.github.com/gists/{gist_id}", headers=_gist_headers(), timeout=20)
    r.raise_for_status()
    raw_url = _gist_get_raw_url(r.json(), filename)
    if not raw_url:
        return ""
    rr = requests.get(raw_url, timeout=20)
    if rr.status_code == 200:
        return rr.text
    return ""

def _gist_write_file(csv_text: str):
    gist_id = st.secrets["GIST_ID"]
    filename = st.secrets["GIST_FILENAME"]
    payload = {"files": {filename: {"content": csv_text}}}
    r = requests.patch(f"https://api.github.com/gists/{gist_id}", headers=_gist_headers(), json=payload, timeout=20)
    r.raise_for_status()

def use_gsheets() -> bool:
    return bool(os.environ.get("GSHEETS_SA_JSON")) and bool(os.environ.get("GSHEETS_SHEET_NAME"))

@st.cache_resource(show_spinner=False)
def _get_gsheets_client():
    """Return the 'Party' worksheet, creating it if needed."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        sa_info = os.environ["GSHEETS_SA_JSON"]
        sheet_name = os.environ["GSHEETS_SHEET_NAME"]
        creds = Credentials.from_service_account_info(
            json.loads(sa_info),
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"],
        )
        client = gspread.authorize(creds)
        sh = client.open_by_url(sheet_name) if sheet_name.startswith("http") else client.open(sheet_name)
        try:
            ws = sh.worksheet("Party")
        except Exception:
            ws = sh.add_worksheet(title="Party", rows=50, cols=10)
            ws.append_row(PARTY_FIELDS)
        return ws
    except Exception as e:
        st.warning(f"Google Sheets not available ({e}). Falling back to CSV.")
        return None

def _defaults() -> Dict[str, str]:
    return {k: "" for k in PARTY_FIELDS}

def read_party() -> Dict[str, str]:
    """Read the single party record."""
    # 1) Gist (primary)
    if use_gist():
        try:
            text = _gist_read_file()
            if text.strip():
                lines = text.splitlines()
                reader = csv.DictReader(lines)
                for r in reader:
                    return {k: r.get(k, "") for k in PARTY_FIELDS}  # first row only
                return _defaults()
        except Exception as e:
            st.warning(f"Gist read failed: {e}")

    # 2) Google Sheets (optional)
    if use_gsheets():
        ws = _get_gsheets_client()
        if ws is not None:
            vals = ws.get_all_values()
            if not vals or len(vals) < 2:
                return _defaults()
            header = vals[0]
            row = vals[1]
            data = dict(zip(header, row))
            for k in PARTY_FIELDS:
                data.setdefault(k, "")
            return {k: data[k] for k in PARTY_FIELDS}

    # 3) Local CSV (fallback)
    if os.path.exists(CSV_FALLBACK_PATH):
        try:
            with open(CSV_FALLBACK_PATH, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    return {k: r.get(k, "") for k in PARTY_FIELDS}
        except Exception:
            pass
    return _defaults()

def write_party(data: Dict[str, str]):
    """Write the single party record."""
    data = {k: str(data.get(k, "")).strip() for k in PARTY_FIELDS}

    # 1) Gist (primary)
    if use_gist():
        try:
            buf = StringIO()
            writer = csv.DictWriter(buf, fieldnames=PARTY_FIELDS)
            writer.writeheader()
            writer.writerow(data)
            _gist_write_file(buf.getvalue())
            return
        except Exception as e:
            st.error(f"Gist write failed: {e}")

    # 2) Google Sheets (optional)
    if use_gsheets():
        ws = _get_gsheets_client()
        if ws is not None:
            ws.clear()
            ws.append_row(PARTY_FIELDS)
            ws.append_row([data[k] for k in PARTY_FIELDS])
            return

    # 3) Local CSV (fallback)
    try:
        with open(CSV_FALLBACK_PATH, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=PARTY_FIELDS)
            writer.writeheader()
            writer.writerow(data)
    except Exception as e:
        st.error(f"Could not save CSV: {e}")

# -----------------------------
# UI
# -----------------------------
def _chips(text: str) -> str:
    """Render comma/semicolon separated items as little pills."""
    items = [x.strip() for x in str(text).replace(";", ",").split(",") if x.strip()]
    if not items:
        return ""
    pills = "".join(
        f"<span style='display:inline-block;padding:4px 10px;margin:3px;border-radius:999px;border:1px solid #e5e7eb;background:#f8fafc'>{x}</span>"
        for x in items
    )
    return pills

def main():
    st.title("☀️ D&D Party Tracker")
    st.caption(f"Streamlit version: **{st.__version__}**")

    # GM key (read-only by default) with safe fallback
    if hasattr(st, "query_params"):
        provided_key = str(st.query_params.get("key", "")).strip()
    else:
        qp = st.experimental_get_query_params()
        provided_key = str(qp.get("key", [""])[0]).strip()

    # EDIT_KEY: prefer secrets; allow env var for local dev
    def _get_edit_key() -> str:
        envk = os.environ.get("EDIT_KEY", "")
        if envk:
            return envk.strip()
        try:
            return str(st.secrets.get("EDIT_KEY", "")).strip()
        except Exception:
            return ""
    EDIT_KEY = _get_edit_key()
    can_edit = bool(EDIT_KEY) and (provided_key == EDIT_KEY)

    if can_edit:
        st.success("GM Edit Mode (key verified)")
    else:
        st.info("Read-only mode. Add your GM key to the URL (?key=...) to edit.")

    # Load party record
    party = read_party()

    # ======== READ VIEW (widgets/cards) ========
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        st.markdown('<div class="badge-title">Your current level is:</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="circle-badge">{party.get("Level","—") or "—"}</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="badge-title">Next Session Date:</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="pill-badge">{party.get("Session Date","—") or "—"}</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="badge-title">Last Location:</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="pill-badge">{party.get("Location","—") or "—"}</div>', unsafe_allow_html=True)

    st.markdown("")
    st.markdown("#### What Happened Last")
    st.markdown(f"<div class='card'>{(party.get('What Happened Last','') or 'No notes yet.')}</div>", unsafe_allow_html=True)

    st.markdown("")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Quests")
        st.markdown(_chips(party.get("Quest Hooks", "")) or "<span class='muted'>None yet.</span>", unsafe_allow_html=True)
    with c2:
        st.markdown("#### Magic Items Found")
        st.markdown(_chips(party.get("Loot/Rewards", "")) or "<span class='muted'>None yet.</span>", unsafe_allow_html=True)

    # ======== GM EDIT FORM ========
    if can_edit:
        st.divider()
        st.subheader("✍️ Edit Party")

        ec1, ec2, ec3 = st.columns(3)
        try:
            level_default = int(party.get("Level") or 1)
        except Exception:
            level_default = 1
        level = ec1.number_input("Level", min_value=1, max_value=30, value=level_default, step=1)
        session_date = ec2.text_input("Session Date (YYYY-MM-DD or text)", value=party.get("Session Date", ""))
        location = ec3.text_input("Location", value=party.get("Location", ""))

        what = st.text_area("What Happened Last (brief)", value=party.get("What Happened Last", ""), height=160)
        h1, h2 = st.columns(2)
        hooks = h1.text_input("Quest Hooks (comma- or semicolon-separated)", value=party.get("Quest Hooks", ""))
        loot  = h2.text_input("Loot/Rewards (comma- or semicolon-separated)", value=party.get("Loot/Rewards", ""))

        if st.button("💾 Save Party"):
            new_data = {
                "Level": str(level),
                "Session Date": session_date.strip(),
                "Location": location.strip(),
                "What Happened Last": what.strip(),
                "Quest Hooks": hooks.strip(),
                "Loot/Rewards": loot.strip(),
            }
            write_party(new_data)
            st.success("Party updated.")
            st.experimental_rerun()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.exception(e)

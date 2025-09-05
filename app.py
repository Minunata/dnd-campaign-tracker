import os
import json
from typing import Dict

import streamlit as st

# -----------------------------
# App Settings
# -----------------------------
st.set_page_config(page_title="D&D Party Tracker", page_icon="☀️", layout="wide")

# ---- Background image (URL) ----
BACKGROUND_URL = "https://media.istockphoto.com/id/1332567781/vector/greek-style-blue-grunge-frame-for-design-or-text.jpg?s=612x612&w=0&k=20&c=tdMOrm4oVi9J2CNn0IjstFK_CpX6hJBXwNUuMnMQj7M="  # <-- change me

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

# --- glassy panels over your background ---
st.markdown("""
<style>
:root{
  --panel-alpha: 0.68;      /* transparency (0=transparent, 1=solid) */
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

/* your cards/badges */
.card{
  background: rgba(var(--panel-bg), var(--panel-alpha));
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  border: 1px solid rgba(255,255,255,0.35);
  border-radius: 16px;
}
.badge{
  background: rgba(var(--panel-bg), var(--panel-alpha));
  border: 1px solid rgba(255,255,255,0.35);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
}
</style>
""", unsafe_allow_html=True)


# One shared party record (order matters)
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
# Storage Backends
# -----------------------------
def use_gsheets() -> bool:
    """Use Google Sheets if env vars are present."""
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
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ],
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
    if use_gsheets():
        ws = _get_gsheets_client()
        if ws is not None:
            vals = ws.get_all_values()
            if not vals or len(vals) < 2:
                return _defaults()
            header = vals[0]
            row = vals[1]
            data = dict(zip(header, row))
            # Ensure all expected fields exist
            for k in PARTY_FIELDS:
                data.setdefault(k, "")
            return {k: data[k] for k in PARTY_FIELDS}
    # CSV fallback
    if os.path.exists(CSV_FALLBACK_PATH):
        try:
            import csv
            with open(CSV_FALLBACK_PATH, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    return {k: r.get(k, "") for k in PARTY_FIELDS}  # first row only
        except Exception:
            pass
    return _defaults()

def write_party(data: Dict[str, str]):
    """Write the single party record."""
    data = {k: str(data.get(k, "")).strip() for k in PARTY_FIELDS}
    if use_gsheets():
        ws = _get_gsheets_client()
        if ws is not None:
            ws.clear()
            ws.append_row(PARTY_FIELDS)
            ws.append_row([data[k] for k in PARTY_FIELDS])
            return
    # CSV fallback
    try:
        import csv
        with open(CSV_FALLBACK_PATH, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=PARTY_FIELDS)
            writer.writeheader()
            writer.writerow(data)
    except Exception as e:
        st.error(f"Could not save CSV: {e}")

# -----------------------------
# UI
# -----------------------------
def main():
    st.title("☀️ D&D Party Tracker")
    st.caption(f"Streamlit version: **{st.__version__}**")

    # --- styling ---
    st.markdown(
        """
        <style>
        .badge-title { font-weight:600; color:#334155; margin: 0 0 6px 2px; }
        .badge {
          display:inline-block; padding:10px 18px; border-radius:999px;
          border:1px solid #e5e7eb; background:#f8fafc;
          font-size:1.25rem; font-weight:700; letter-spacing:0.3px;
        }
        .card { padding:14px 16px; border:1px solid #e5e7eb; border-radius:16px; background:#ffffff; }
        .muted { color:#64748b; font-size:0.9rem; }
        </style>
        """,
        unsafe_allow_html=True
    )

    # GM key (read-only by default) with safe fallback for older Streamlit
    if hasattr(st, "query_params"):
        params = st.query_params
        provided_key = str(params.get("key", "")).strip()
    else:
        qp = st.experimental_get_query_params()
        provided_key = str(qp.get("key", [""])[0]).strip()

    EDIT_KEY = str(st.secrets.get("EDIT_KEY", "")).strip()
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
        st.markdown(f'<div class="badge">{party.get("Level","—") or "—"}</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="badge-title">Session Date:</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="badge">{party.get("Session Date","—") or "—"}</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="badge-title">Location:</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="badge">{party.get("Location","—") or "—"}</div>', unsafe_allow_html=True)

    st.markdown("")
    st.markdown("#### What Happened Last")
    st.markdown(f"<div class='card'>{(party.get('What Happened Last','') or '_No notes yet._')}</div>", unsafe_allow_html=True)

    st.markdown("")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Quest Hooks")
        st.markdown(_chips(party.get("Quest Hooks", "")) or "<span class='muted'>None yet.</span>", unsafe_allow_html=True)
    with c2:
        st.markdown("#### Loot / Rewards")
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

# helper moved below main so we can show exceptions if it fails to load
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

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Surface any errors instead of a blank screen
        st.exception(e)




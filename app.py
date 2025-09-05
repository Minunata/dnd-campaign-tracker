import os
import io
import time
from typing import Optional, List
import pandas as pd
import streamlit as st
import json

# -----------------------------
# App Settings
# -----------------------------
st.set_page_config(page_title="D&D Campaign Tracker", page_icon="📜", layout="wide")

DEFAULT_COLUMNS = [
    "Player",
    "Character",
    "Level",
    "XP",
    "Session Date",
    "Location",
    "What Happened Last",
    "Quest Hooks",
    "Loot/Rewards",
]

CSV_FALLBACK_PATH = "campaign_tracker.csv"

# -----------------------------
# Storage Backends
# -----------------------------
def use_gsheets() -> bool:
    """
    Returns True if Google Sheets env vars are present.
    Expected env vars:
      - GSHEETS_SA_JSON: contents of the service account JSON (string)
      - GSHEETS_SHEET_NAME: the spreadsheet's name or URL
    """
    return bool(os.environ.get("GSHEETS_SA_JSON")) and bool(os.environ.get("GSHEETS_SHEET_NAME"))

@st.cache_resource(show_spinner=False)
def _get_gsheets_client():
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        sa_info = os.environ["GSHEETS_SA_JSON"]
        sheet_name = os.environ["GSHEETS_SHEET_NAME"]  # name or url

        # Create credentials from the JSON string
        creds = Credentials.from_service_account_info(
            json.loads(sa_info),
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ],
        )
        client = gspread.authorize(creds)
        sh = client.open_by_url(sheet_name) if sheet_name.startswith("http") else client.open(sheet_name)

        # Create or open the first worksheet named "Tracker"
        try:
            ws = sh.worksheet("Tracker")
        except Exception:
            ws = sh.add_worksheet(title="Tracker", rows=1000, cols=20)
            ws.append_row(DEFAULT_COLUMNS)
        return ws
    except Exception as e:
        st.warning(f"Google Sheets not available ({e}). Falling back to CSV.")
        return None

def read_data() -> pd.DataFrame:
    if use_gsheets():
        ws = _get_gsheets_client()
        if ws is not None:
            vals = ws.get_all_values()
            if not vals:
                return pd.DataFrame(columns=DEFAULT_COLUMNS)
            header = vals[0]
            rows = vals[1:]
            df = pd.DataFrame(rows, columns=header)
            # Normalize columns
            for col in DEFAULT_COLUMNS:
                if col not in df.columns:
                    df[col] = ""
            df = df[DEFAULT_COLUMNS]
            return df
    # CSV fallback
    if os.path.exists(CSV_FALLBACK_PATH):
        df = pd.read_csv(CSV_FALLBACK_PATH)
        for col in DEFAULT_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        return df[DEFAULT_COLUMNS]
    else:
        return pd.DataFrame(columns=DEFAULT_COLUMNS)

def write_data(df: pd.DataFrame):
    df = df.fillna("")
    if use_gsheets():
        ws = _get_gsheets_client()
        if ws is not None:
            # Clear and write
            ws.clear()
            ws.append_row(DEFAULT_COLUMNS)
            if len(df) > 0:
                ws.update(f"A2", [df[col].astype(str).tolist() for col in DEFAULT_COLUMNS], raw=False, major_dimension="COLUMNS")
            return
    # CSV fallback
    df.to_csv(CSV_FALLBACK_PATH, index=False)

# -----------------------------
# Helpers
# -----------------------------
def coerce_int(s: str) -> str:
    try:
        return str(int(float(s)))
    except:
        return s

def clean_df_types(df: pd.DataFrame) -> pd.DataFrame:
    if "Level" in df.columns:
        df["Level"] = df["Level"].astype(str).map(coerce_int)
    if "XP" in df.columns:
        df["XP"] = df["XP"].astype(str).map(lambda x: x if x.strip() == "" else coerce_int(x))
    return df

def add_row(df: pd.DataFrame, template: Optional[dict] = None) -> pd.DataFrame:
    row = {c: "" for c in DEFAULT_COLUMNS}
    if template:
        row.update({k:v for k,v in template.items() if k in row})
    return pd.concat([df, pd.DataFrame([row])], ignore_index=True)

def delete_rows(df: pd.DataFrame, indices: List[int]) -> pd.DataFrame:
    return df.drop(indices).reset_index(drop=True)

# -----------------------------
# UI
# -----------------------------
def main():
    st.title("📜 D&D Campaign Tracker")
    st.caption("Track party levels, last-session notes, and hooks—share a read-only link with your players.")

    # Query param for GM edit key (default is read-only)
    params = st.query_params()
    provided_key = params.get("key", [""])[0]
    EDIT_KEY = st.secrets.get("EDIT_KEY", "")
    can_edit = EDIT_KEY and (provided_key == EDIT_KEY)

    if can_edit:
        st.success("GM Edit Mode (key verified)")
    else:
        st.info("Read-only mode. Add your GM key to the URL (?key=...) to edit.")

    # Load data
    df = read_data()
    df = clean_df_types(df)

    # Sidebar: Controls
    st.sidebar.header("View Options")
    if can_edit:
        st.sidebar.info("Public mode: read-only view")
    sort_col = st.sidebar.selectbox("Sort by", DEFAULT_COLUMNS, index=0)
    asc = st.sidebar.checkbox("Ascending", value=True)
    search = st.sidebar.text_input("Search (any field)", "")

    # Filter + sort
    view = df.copy()
    if search.strip():
        mask = pd.Series(False, index=view.index)
        for c in DEFAULT_COLUMNS:
            mask = mask | view[c].astype(str).str.contains(search, case=False, na=False)
        view = view[mask]
    view = view.sort_values(by=sort_col, ascending=asc)

    # Show table
    st.subheader("Party / Session Table")
    st.dataframe(view, use_container_width=True, hide_index=True)

    # Add/Edit (GM Only)
    if can_edit:
        st.divider()
        st.subheader("✍️ Edit Tracker")

        with st.expander("Add a new row"):
            c1, c2, c3, c4 = st.columns(4)
            player = c1.text_input("Player", "")
            character = c2.text_input("Character", "")
            level = c3.number_input("Level", min_value=1, max_value=30, value=1, step=1)
            xp = c4.text_input("XP (optional)", "")
            c5, c6 = st.columns(2)
            session_date = c5.date_input("Session Date", value=None, format="YYYY-MM-DD")
            location = c6.text_input("Location", "")
            what = st.text_area("What Happened Last (brief)", "")
            hooks = st.text_area("Quest Hooks (comma-separated)", "")
            loot = st.text_area("Loot/Rewards (comma-separated)", "")

            if st.button("➕ Add Row"):
                row = {
                    "Player": player,
                    "Character": character,
                    "Level": str(level),
                    "XP": xp,
                    "Session Date": str(session_date) if session_date else "",
                    "Location": location,
                    "What Happened Last": what,
                    "Quest Hooks": hooks,
                    "Loot/Rewards": loot,
                }
                df2 = add_row(df, row)
                write_data(df2)
                st.success("Row added.")
                st.experimental_rerun()

        st.markdown("#### Bulk Edit (spreadsheet style)")
        edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="editor")
        if st.button("💾 Save Changes"):
            write_data(clean_df_types(edited))
            st.success("Saved!")
            st.experimental_rerun()

        st.markdown("#### Delete Rows")
        to_delete = st.multiselect("Select rows to delete (by index)", options=list(range(len(df))), default=[])
        if st.button("🗑️ Delete Selected"):
            df2 = delete_rows(df, to_delete)
            write_data(df2)
            st.success(f"Deleted {len(to_delete)} row(s).")
            st.experimental_rerun()

    # Export
    st.divider()
    st.subheader("📤 Export / Share")
    st.download_button("Download CSV", data=df.to_csv(index=False), file_name="campaign_tracker_export.csv", mime="text/csv")
    st.caption("Share the base URL with players (read-only). To edit, append ?key=YOUR_EDIT_KEY to the URL.")

if __name__ == "__main__":
    main()

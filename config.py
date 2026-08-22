import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

ICON_URL = "https://cdn-icons-png.flaticon.com/512/2953/2953361.png"

# --- ΚΑΤΗΓΟΡΙΕΣ ΕΣΟΔΩΝ & ΕΞΟΔΩΝ ---
INCOME_CATEGORIES = [
    "Μισθός",
    "Freelance / Ιδιωτικά",
    "Επενδύσεις / Μερίσματα",
    "Επιστροφή Χρημάτων",
    "Δώρα / Επιδόματα",
    "Άλλο Έσοδο"
]

EXPENSE_CATEGORIES = [
    "Σούπερ Μάρκετ / Τρόφιμα",
    "Ενοίκιο / Λογαριασμοί",
    "Μετακινήσεις / Καύσιμα",
    "Φαγητό έξω / Καφέδες",
    "Διασκέδαση / Συνδρομές",
    "Αγορές / Ρούχα",
    "Υγεία / Φάρμακα",
    "Εκπαίδευση / Σεμινάρια",
    "Ταξίδια / Διακοπές",
    "Έκτακτα Έξοδα"
]

@st.cache_resource
def get_sheets_connection():
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        if "gcp_service_account" not in st.secrets:
            raise Exception("Δεν βρέθηκε το [gcp_service_account] στα Streamlit Secrets.")

        creds_dict = dict(st.secrets["gcp_service_account"])
        
        # Αντικατάσταση διπλών backslashes αν υπάρχουν
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

        credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(credentials)

        # Σύνδεση με το Google Sheet
        spreadsheet = client.open("Personal Finance Tracker Data")
        worksheet = spreadsheet.worksheet("Sheet1")
        users_sheet = spreadsheet.worksheet("Users")

        return worksheet, users_sheet

    except Exception as e:
        raise Exception(f"Σφάλμα σύνδεσης με το Google Sheet: {e}")

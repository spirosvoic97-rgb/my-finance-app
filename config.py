import streamlit as st
import gspread
import json
import base64
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
        
        # 1. Έλεγχος για connections.gsheets με private_key_base64
        if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
            gs_sec = st.secrets["connections"]["gsheets"]
            if "private_key_base64" in gs_sec:
                # Αποκωδικοποίηση του Base64 JSON
                decoded_bytes = base64.b64decode(gs_sec["private_key_base64"])
                creds_info = json.loads(decoded_bytes.decode("utf-8"))
                credentials = Credentials.from_service_account_info(creds_info, scopes=scopes)
            else:
                creds_dict = dict(gs_sec)
                if "private_key" in creds_dict:
                    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
                credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
                
        # 2. Fallback σε gcp_service_account
        elif "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        else:
            raise Exception("Δεν βρέθηκαν έγκυρα Google Credentials στα Secrets.")

        client = gspread.authorize(credentials)

        # Σύνδεση με το Google Sheet
        spreadsheet = client.open("Personal Finance Tracker Data")
        worksheet = spreadsheet.worksheet("Sheet1")
        users_sheet = spreadsheet.worksheet("Users")

        return worksheet, users_sheet

    except Exception as e:
        raise Exception(f"Σφάλμα σύνδεσης με το Google Sheet: {e}")

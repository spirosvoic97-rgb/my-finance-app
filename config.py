import streamlit as st
import gspread
import json
import base64
from google.oauth2.service_account import Credentials

ICON_URL = "https://cdn-icons-png.flaticon.com/512/2953/2953361.png"

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
        
        if "gcp_service_account" not in st.secrets or "json_b64" not in st.secrets["gcp_service_account"]:
            raise Exception("Δεν βρέθηκε το json_b64 στα Secrets.")

        # 1. Ανάγνωση Base64 string
        raw_b64 = str(st.secrets["gcp_service_account"]["json_b64"]).strip()
        
        # 2. Καθαρισμός από τυχόν εισαγωγικά
        if (raw_b64.startswith('"') and raw_b64.endswith('"')) or (raw_b64.startswith("'") and raw_b64.endswith("'")):
            raw_b64 = raw_b64[1:-1]

        # FIX: Αυτόματη προσθήκη padding αν λείπει
        raw_b64 += "=" * ((4 - len(raw_b64) % 4) % 4)

        # 3. Αποκωδικοποίηση Base64
        decoded_bytes = base64.b64decode(raw_b64)

        credentials = Credentials.from_service_account_info(creds_info, scopes=scopes)
        client = gspread.authorize(credentials)

        spreadsheet = client.open("Personal Finance Tracker Data")
        worksheet = spreadsheet.worksheet("Sheet1")
        users_sheet = spreadsheet.worksheet("Users")

        return worksheet, users_sheet

    except Exception as e:
        raise Exception(f"Σφάλμα σύνδεσης με το Google Sheet: {e}")

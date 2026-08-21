import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import base64

# --- CONSTANTS ---
ICON_URL = "https://raw.githubusercontent.com/spirosvoic97-rgb/my-finance-app/main/icon.png"
INCOME_CATEGORIES = ["Άλλα Έσοδα / Έκτακτα", "Ιδιαίτερα", "Σχολή Χορού / Ωδείο ΑΜ", "Φροντιστήριο"]
EXPENSE_CATEGORIES = ["Super Market", "Αποταμίευση", "Διασκέδαση / Έξοδος", "Έκτακτα / Δώρα / Ταξίδια", "Μετακινήσεις", "Πάγια / Λογαριασμοί", "Προσωπικά / Χόμπι", "Επαγγελματικά Έξοδα"]

# --- GOOGLE SHEETS SETUP ---
@st.cache_resource
def get_sheets_connection():
    creds_dict = dict(st.secrets["connections"]["gsheets"])
    decoded_key = base64.b64decode(creds_dict["private_key_base64"]).decode("utf-8")
    creds_dict["private_key"] = decoded_key.replace("\\n", "\n")
    del creds_dict["private_key_base64"]

    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    gc = gspread.authorize(credentials)

    try:
        sh = gc.open("Finance Tracker Data")
    except gspread.exceptions.SpreadsheetNotFound:
        sh = gc.create("Finance Tracker Data")

    try:
        worksheet = sh.worksheet("Data")
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sh.get_worksheet(0)
        worksheet.update_title("Data")
        worksheet.append_row(["Ημερομηνία", "Περιγραφή", "Τύπος", "Κατηγορία", "Ποσό", "Επαναλαμβανόμενο", "Username"])

    try:
        users_sheet = sh.worksheet("Users")
    except gspread.exceptions.WorksheetNotFound:
        users_sheet = sh.add_worksheet(title="Users", rows="100", cols="5")
        users_sheet.append_row(["Username", "PasswordHash", "CreatedAt", "Email", "StartingBalance"])

    return worksheet, users_sheet

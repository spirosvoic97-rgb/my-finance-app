import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

ICON_URL = "https://cdn-icons-png.flaticon.com/512/2953/2953361.png"

@st.cache_resource
def get_sheets_connection():
    try:
        # Δημιουργία credentials από τα Secrets
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            
            # Διόρθωση newlines στο private_key αν χρειάζεται
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
                
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            
            credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            client = gspread.authorize(credentials)
        else:
            raise Exception("Δεν βρέθηκαν τα [gcp_service_account] στα Streamlit Secrets.")

        # Σύνδεση με το Google Sheet
        spreadsheet = client.open("Personal Finance Tracker Data")
        worksheet = spreadsheet.worksheet("Sheet1")
        users_sheet = spreadsheet.worksheet("Users")

        return worksheet, users_sheet

    except Exception as e:
        raise Exception(f"Σφάλμα σύνδεσης με το Google Sheet: {e}")

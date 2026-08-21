# --- GOOGLE SHEETS SETUP ---
@st.cache_resource
def get_sheets_connection():
    creds_dict = dict(st.secrets["connections"]["gsheets"])
    
    # Ασφαλής προσθήκη Padding για το Base64
    b64_str = creds_dict["private_key_base64"].strip()
    missing_padding = len(b64_str) % 4
    if missing_padding:
        b64_str += '=' * (4 - missing_padding)

    decoded_key = base64.b64decode(b64_str).decode("utf-8")
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

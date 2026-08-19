import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
import base64
from io import BytesIO
import datetime
import calendar
import re
import hashlib
from PIL import Image

st.set_page_config(page_title="Personal Finance Tracker PRO", page_icon="💰", layout="wide")

# --- PWA HEAD INJECTION ---
st.markdown(
    """
    <head>
        <link rel="manifest" href="./manifest.json">
        <meta name="theme-color" content="#11151C">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <meta name="apple-mobile-web-app-title" content="FinancePRO">
        <link rel="apple-touch-icon" href="https://cdn-icons-png.flaticon.com/512/2845/2845828.png">
        <script>
            if ('serviceWorker' in navigator) {
                window.addEventListener('load', function() {
                    navigator.serviceWorker.register('./service-worker.js');
                });
            }
        </script>
    </head>
    """,
    unsafe_allow_html=True
)

# --- HELPER: HASH PASSWORD ---
def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hash(password, hashed_text):
    if make_hash(password) == hashed_text:
        return True
    return False

# --- GOOGLE SHEETS AUTHENTICATION & SETUP ---
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

# 1o Φύλλο: Δεδομένα
try:
    worksheet = sh.worksheet("Data")
except gspread.exceptions.WorksheetNotFound:
    worksheet = sh.get_worksheet(0)
    worksheet.update_title("Data")
    worksheet.append_row(["Ημερομηνία", "Περιγραφή", "Τύπος", "Κατηγορία", "Ποσό", "Επαναλαμβανόμενο"])

# 2ο Φύλλο: Χρήστες
try:
    users_sheet = sh.worksheet("Users")
except gspread.exceptions.WorksheetNotFound:
    users_sheet = sh.add_worksheet(title="Users", rows="100", cols="3")
    users_sheet.append_row(["Username", "PasswordHash", "CreatedAt"])

# --- LOGIN & SIGNUP AUTHENTICATION SYSTEM ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.title("🔒 Πρόσβαση στην Εφαρμογή")
        
        tab_login, tab_signup = st.tabs(["🔑 Σύνδεση", "📝 Εγγραφή Νέου Χρήστη"])
        
        # TAB 1: Σύνδεση
        with tab_login:
            col1, col2 = st.columns([1, 2])
            with col1:
                username = st.text_input("Χρήστης", key="login_user")
                password = st.text_input("Κωδικός", type="password", key="login_pass")
                if st.button("Σύνδεση", key="login_btn"):
                    # 1. Έλεγχος στα secrets
                    secrets_valid = False
                    if "passwords" in st.secrets and username in st.secrets["passwords"]:
                        if password == st.secrets["passwords"][username]:
                            secrets_valid = True

                    # 2. Έλεγχος στο φύλλο Users
                    sheet_valid = False
                    try:
                        users_data = users_sheet.get_all_records()
                        for u in users_data:
                            if str(u.get("Username")) == username and check_hash(password, str(u.get("PasswordHash"))):
                                sheet_valid = True
                                break
                    except Exception:
                        pass

                    if secrets_valid or sheet_valid:
                        st.session_state["authenticated"] = True
                        st.session_state["current_user"] = username
                        st.success("✅ Επιτυχής σύνδεση!")
                        st.rerun()
                    else:
                        st.error("❌ Λάθος όνομα χρήστη ή κωδικός πρόσβασης")
                        
        # TAB 2: Εγγραφή Νέου Χρήστη
        with tab_signup:
            col1, col2 = st.columns([1, 2])
            with col1:
                new_username = st.text_input("Νέο Όνομα Χρήστη", key="signup_user")
                new_password = st.text_input("Νέος Κωδικός", type="password", key="signup_pass")
                confirm_password = st.text_input("Επιβεβαίωση Κωδικού", type="password", key="signup_confirm")
                
                if st.button("Δημιουργία Λογαριασμού", key="signup_btn"):
                    if not new_username or not new_password:
                        st.warning("⚠️ Παρακαλώ συμπλήρωσε όλα τα πεδία.")
                    elif new_password != confirm_password:
                        st.error("❌ Οι κωδικοί πρόσβασης δεν ταιριάζουν!")
                    elif len(new_password) < 4:
                        st.warning("⚠️ Ο κωδικός πρέπει να έχει τουλάχιστον 4 χαρακτήρες.")
                    else:
                        # Έλεγχος αν υπάρχει ήδη το username
                        existing_users = []
                        try:
                            users_data = users_sheet.get_all_records()
                            existing_users = [str(u.get("Username")).lower() for u in users_data]
                        except Exception:
                            pass

                        if new_username.lower() in existing_users:
                            st.error("❌ Το όνομα χρήστη υπάρχει ήδη! Διάλεξε άλλο.")
                        else:
                            pass_hash = make_hash(new_password)
                            created_at = str(datetime.date.today())
                            users_sheet.append_row([new_username, pass_hash, created_at])
                            st.success("🎉 Ο λογαριασμός δημιουργήθηκε επιτυχώς! Μπορείς τώρα να συνδεθείς.")
        return False
    return True

if check_password():
    STARTING_BALANCE = 672.776

    # Διάβασμα δεδομένων
    try:
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty and "Ημερομηνία" in df.columns:
            df["Ημερομηνία"] = pd.to_datetime(df["Ημερομηνία"], errors="coerce").dt.strftime("%Y-%m-%d")
            df["Ποσό"] = pd.to_numeric(df["Ποσό"], errors="coerce").fillna(0.0)
            df = df.dropna(subset=["Ημερομηνία"])
    except Exception:
        df = pd.DataFrame(columns=["Ημερομηνία", "Περιγραφή", "Τύπος", "Κατηγορία", "Ποσό", "Επαναλαμβανόμενο"])

    INCOME_CATEGORIES = ["Άλλα Έσοδα / Έκτακτα", "Ιδιαίτερα", "Σχολή Χορού / Ωδείο ΑΜ", "Φροντιστήριο"]
    EXPENSE_CATEGORIES = ["Super Market", "Αποταμίευση", "Διασκέδαση / Έξοδος", "Έκτακτα / Δώρα / Ταξίδια", "Μετακινήσεις", "Πάγια / Λογαριασμοί", "Προσωπικά / Χόμπι", "Επαγγελματικά Έξοδα"]

    st.title("📊 Financial Dashboard & Waterfall Tracker PRO")

    # --- SIDEBAR: Φίλτρα & Theme ---
    st.sidebar.header("🎨 Εμφάνιση")
    theme = st.sidebar.radio("Θέμα Εμφάνισης", ["Dark Mode 🌙", "Light Mode ☀️"])
    
    if "current_user" in st.session_state:
        st.sidebar.caption(f"👤 Συνδεδεμένος ως: **{st.session_state['current_user']}**")
        if st.sidebar.button("🚪 Αποσύνδεση"):
            st.session_state["authenticated"] = False
            st.session_state["current_user"] = ""
            st.rerun()

    if theme == "Light Mode ☀️":
        plotly_template = "plotly_white"
        chart_bg = "#FFFFFF"
        chart_font_color = "#111111"
        chart_grid_color = "#D1D5DB"
        
        st.markdown(
            """
            <style>
            .stApp, [data-testid="stSidebar"], [data-testid="stHeader"], [data-testid="stAppToolbar"], header {
                background-color: #FFFFFF !important;
                color: #111111 !important;
            }
            [data-testid="stHeader"] img, [data-testid="stAppToolbar"] img, 
            [data-testid="stHeader"] svg, [data-testid="stAppToolbar"] svg,
            header svg, button[kind="header"] svg {
                filter: invert(1) !important;
            }
            [data-testid="stHeader"] button, [data-testid="stAppToolbar"] button {
                color: #111111 !important;
                background-color: #FFFFFF !important;
            }
            h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {
                color: #111111 !important;
            }
            input, select, textarea, div[role="combobox"], [data-baseweb="select"] {
                background-color: #FFFFFF !important;
                color: #111111 !important;
                border: 1px solid #111111 !important;
                border-radius: 6px !important;
            }
            [data-baseweb="select"] * {
                background-color: #FFFFFF !important;
                color: #111111 !important;
            }
            [data-baseweb="select"] svg {
                fill: #111111 !important;
            }
            [data-testid="stNumberInput"] button {
                background-color: #FFFFFF !important;
                color: #111111 !important;
                border: 1px solid #111111 !important;
            }
            [data-testid="stNumberInput"] button * {
                color: #111111 !important;
                fill: #111111 !important;
            }
            [data-testid="stExpander"] {
                background-color: #FFFFFF !important;
                border: 1px solid #111111 !important;
                border-radius: 6px !important;
            }
            [data-testid="stExpander"] details, [data-testid="stExpander"] summary {
                background-color: #FFFFFF !important;
                color: #111111 !important;
            }
            [data-testid="stExpander"] summary * {
                color: #111111 !important;
                fill: #111111 !important;
            }
            .stButton > button, button[aria-haspopup="dialog"], .stDownloadButton > button {
                background-color: #FFFFFF !important;
                color: #111111 !important;
                border: 1px solid #111111 !important;
                font-weight: bold !important;
            }
            .stButton > button:hover, button[aria-haspopup="dialog"]:hover, .stDownloadButton > button:hover {
                background-color: #F0F2F6 !important;
                border: 1px solid #000000 !important;
                color: #000000 !important;
            }
            hr { border-color: #E0E0E0 !important; }
            </style>
            """,
            unsafe_allow_html=True
        )
    else:
        plotly_template = "plotly_dark"
        chart_bg = "#11151C"
        chart_font_color = "#FFFFFF"
        chart_grid_color = "#333333"

    # --- ADVANCED RECEIPT PARSER & SCANNER ---
    st.sidebar.markdown("---")
    st.sidebar.header("📸 Receipt Scanner (OCR)")
    uploaded_receipt = st.sidebar.file_uploader("Ανέβασμα Απόδειξης (JPG/PNG)", type=["jpg", "png", "jpeg"])

    scanned_amount = 0.0
    scanned_desc = ""
    scanned_category = "Super Market"

    if uploaded_receipt is not None:
        st.sidebar.image(uploaded_receipt, caption="Απόδειξη", use_container_width=True)
        
        try:
            img = Image.open(uploaded_receipt).convert('L')
            
            import pytesseract
            extracted_text = pytesseract.image_to_string(img, lang='ell+eng', config='--psm 6')
            
            amounts = re.findall(r'\b\d+[\.,]\d{2}\b', extracted_text)
            if amounts:
                clean_amounts = [float(a.replace(',', '.')) for a in amounts if float(a.replace(',', '.')) < 2000]
                if clean_amounts:
                    scanned_amount = max(clean_amounts)
            
            text_lower = extracted_text.lower()
            if any(w in text_lower for w in ["μασούτης", "σκλαβενίτης", "lidl", "αβ", "super"]):
                scanned_desc = "Super Market"
                scanned_category = "Super Market"
            elif any(w in text_lower for w in ["bp", "shell", "eko", "diesel", "βενζίνη", "καύσιμα", "πρατήριο"]):
                scanned_desc = "Πρατήριο Καυσίμων"
                scanned_category = "Μετακινήσεις"
            else:
                scanned_desc = "Αγορά από Απόδειξη"
                
        except Exception:
            filename = uploaded_receipt.name.lower()
            if "masoutis" in filename or "super" in filename or "178715" in filename:
                scanned_desc = "Super Market"
                scanned_category = "Super Market"
            else:
                scanned_desc = "Νέα Απόδειξη"
                scanned_category = "Super Market"

        st.sidebar.markdown("**🔍 Επιβεβαίωση / Διόρθωση Σάρωσης:**")
        scanned_amount = st.sidebar.number_input("Ποσό (€)", value=float(scanned_amount), step=0.10, key="scan_amt_confirm")
        scanned_desc = st.sidebar.text_input("Περιγραφή", value=scanned_desc if scanned_desc else "Απόδειξη", key="scan_desc_confirm")
        scanned_category = st.sidebar.selectbox("Κατηγορία", EXPENSE_CATEGORIES, index=EXPENSE_CATEGORIES.index(scanned_category) if scanned_category in EXPENSE_CATEGORIES else 0, key="scan_cat_confirm")

        if st.sidebar.button("📥 Άμεση Καταχώρηση Απόδειξης"):
            today_str = str(datetime.date.today())
            worksheet.append_row([today_str, scanned_desc, "Έξοδο", scanned_category, scanned_amount, "Όχι"], value_input_option="USER_ENTERED")
            st.cache_data.clear()
            st.sidebar.success("🎉 Η απόδειξη καταχωρήθηκε επιτυχώς!")
            st.rerun()

    # --- SMART QUICK LOG ---
    st.sidebar.markdown("---")
    st.sidebar.header("⚡ Smart Quick Log")
    st.sidebar.caption("Γράψε π.χ. *15 σουβλάκια* ή *500 ιδιαίτερα*")
    quick_input = st.sidebar.text_input("Γρήγορη Γραπτή Καταχώρηση", key="quick_input_key")

    if st.sidebar.button("⚡ Γρήγορη Προσθήκη"):
        if quick_input:
            match = re.search(r"(\d+(?:\.\d+)?)", quick_input)
            if match:
                extracted_amount = float(match.group(1))
                extracted_desc = quick_input.replace(match.group(1), "").strip()
                
                desc_lower = extracted_desc.lower()
                auto_type = "Έξοδο"
                auto_cat = "Διασκέδαση / Έξοδος"

                if any(w in desc_lower for w in ["ιδιαίτερα", "μισθός", "φροντιστήριο", "ωδείο", "έσοδο", "πληρωμή"]):
                    auto_type = "Έσοδο"
                    if "ιδιαίτερα" in desc_lower: auto_cat = "Ιδιαίτερα"
                    elif "φροντιστήριο" in desc_lower: auto_cat = "Φροντιστήριο"
                    else: auto_cat = "Άλλα Έσοδα / Έκτακτα"
                else:
                    if any(w in desc_lower for w in ["super", "market", "φαγητό", "μάρκετ", "τόστ", "σουβλάκια"]): auto_cat = "Super Market"
                    elif any(w in desc_lower for w in ["βενζίνη", "κάρτα", "διόδια", "bus", "diesel"]): auto_cat = "Μετακινήσεις"
                    elif any(w in desc_lower for w in ["δεη", "νερό", "ενοίκιο", "cosmote", "ιντερνετ"]): auto_cat = "Πάγια / Λογαριασμοί"

                today_str = str(datetime.date.today())
                worksheet.append_row([today_str, extracted_desc if extracted_desc else "Γρήγορη Καταχώρηση", auto_type, auto_cat, extracted_amount, "Όχι"], value_input_option="USER_ENTERED")
                st.cache_data.clear()
                st.sidebar.success(f"Προστέθηκε: {extracted_desc} - {extracted_amount}€ ({auto_cat})")
                st.rerun()

    # --- SIDEBAR: Φίλτρα ---
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Φίλτρα Προβολής")
    if not df.empty and "Ημερομηνία" in df.columns:
        temp_years = pd.to_datetime(df["Ημερομηνία"], errors="coerce").dt.year.dropna().astype(int).unique()
        years = sorted(list(temp_years), reverse=True)
        selected_year = st.sidebar.selectbox("Έτος", ["Όλα"] + list(years))
        selected_month = st.sidebar.selectbox("Μήνας", ["Όλοι", 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
        search_query = st.sidebar.text_input("🔎 Αναζήτηση Περιγραφής", "")
    else:
        selected_year, selected_month, search_query = "Όλα", "Όλοι", ""

    st.sidebar.markdown("---")
    st.sidebar.header("⚙️ Όρια Προϋπολογισμού")
    with st.sidebar.expander("Ρύθμιση Ορίων ανά Κατηγορία"):
        limit_fun = st.number_input("Διασκέδαση / Έξοδος (€)", value=300.0, step=50.0)
        limit_sm = st.number_input("Super Market (€)", value=200.0, step=50.0)
        limit_hobby = st.number_input("Προσωπικά / Χόμπι (€)", value=150.0, step=50.0)

    BUDGET_LIMITS = {
        "Διασκέδαση / Έξοδος": limit_fun,
        "Super Market": limit_sm,
        "Προσωπικά / Χόμπι": limit_hobby
    }

    # --- SIDEBAR: Χειροκίνητη Καταχώρηση ---
    st.sidebar.markdown("---")
    st.sidebar.header("➕ Νέα Καταχώρηση")
    entry_type = st.sidebar.radio("Τύπος", ["Έσοδο", "Έξοδο"])
    date = st.sidebar.date_input("Ημερομηνία")
    description = st.sidebar.text_input("Περιγραφή", value="")
    
    cats = INCOME_CATEGORIES if entry_type == "Έσοδο" else EXPENSE_CATEGORIES
    category = st.sidebar.selectbox("Κατηγορία", cats)
    
    amount = st.sidebar.number_input("Ποσό (€)", value=0.0, min_value=0.0, format="%.2f")
    is_recurring = st.sidebar.checkbox("🔄 Επαναλαμβανόμενο (Μηνιαίο)")

    if st.sidebar.button("Αποθήκευση"):
        rec_val = "Ναι" if is_recurring else "Όχι"
        worksheet.append_row([str(date), description, entry_type, category, float(amount), rec_val], value_input_option="USER_ENTERED")
        st.cache_data.clear()
        st.sidebar.success("Η εγγραφή αποθηκεύτηκε επιτυχώς!")
        st.rerun()

    # --- ΦΙΛΤΡΑΡΙΣΜΑ ΔΕΔΟΜΕΝΩΝ ---
    filtered_df = df.copy()
    if not filtered_df.empty and "Ημερομηνία" in filtered_df.columns:
        temp_dates = pd.to_datetime(filtered_df["Ημερομηνία"], errors="coerce")
        if selected_year != "Όλα":
            filtered_df = filtered_df[temp_dates.dt.year == int(selected_year)]
            temp_dates = pd.to_datetime(filtered_df["Ημερομηνία"], errors="coerce")
        if selected_month != "Όλοι":
            filtered_df = filtered_df[temp_dates.dt.month == int(selected_month)]
        if search_query:
            filtered_df = filtered_df[filtered_df["Περιγραφή"].astype(str).str.contains(search_query, case=False, na=False)]
            
    total_income = filtered_df[filtered_df["Τύπος"] == "Έσοδο"]["Ποσό"].sum() if not filtered_df.empty else 0.0
    total_expenses = filtered_df[filtered_df["Τύπος"] == "Έξοδο"]["Ποσό"].sum() if not filtered_df.empty else 0.0
    net_month = total_income - total_expenses
        
    overall_income = df[df["Τύπος"] == "Έσοδο"]["Ποσό"].sum() if not df.empty else 0.0
    overall_expenses = df[df["Τύπος"] == "Έξοδο"]["Ποσό"].sum() if not df.empty else 0.0
    final_balance = STARTING_BALANCE + (overall_income - overall_expenses)

    # --- SAFE TO SPEND CALCULATOR & ALERT ---
    now = datetime.date.today()
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    days_remaining = (days_in_month - now.day) + 1
    safe_to_spend_daily = (final_balance / days_remaining) if final_balance > 0 and days_remaining > 0 else 0.0

    if safe_to_spend_daily < 10.0:
        st.error(f"🚨 **Alert Χαμηλού Ημερήσιου Ορίου:** Το ημερήσιο διαθέσιμο υπόλοιπό σου (`Safe-to-Spend`) έπεσε στα **{safe_to_spend_daily:.2f} € / ημέρα** για τις {days_remaining} ημέρες που απομένουν στο μήνα!")

    # --- DASHBOARD METRICS ---
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1.2])
    col1.metric("Αρχικό Ταμείο", f"{STARTING_BALANCE:.2f} €")
    col2.metric("Επιλεγμένα Έσοδα", f"{total_income:.2f} €")
    col3.metric("Επιλεγμένα Έξοδα", f"{total_expenses:.2f} €")
    col4.metric("Συνολικό Υπόλοιπο", f"{final_balance:.2f} €")
    col5.metric("💡 Safe-to-Spend / Ημέρα", f"{safe_to_spend_daily:.2f} €", help=f"Ασφαλές ημερήσιο όριο εξόδων για τις {days_remaining} ημέρες που απομένουν στο μήνα.")

    st.markdown("---")

    # --- ALERTS ---
    if not filtered_df.empty:
        exp_by_cat = filtered_df[filtered_df["Τύπος"] == "Έξοδο"].groupby("Κατηγορία")["Ποσό"].sum()
        for cat, limit in BUDGET_LIMITS.items():
            if limit > 0 and cat in exp_by_cat and exp_by_cat[cat] > limit:
                st.warning(f"⚠️ **Υπέρβαση Ορίου:** Τα έξοδα στην κατηγορία **{cat}** έφτασαν τα **{exp_by_cat[cat]:.2f} €** (Όριο: {limit:.2f} €)!")

    # --- GRAPHICAL CHARTS (WATERFALL + PIE CHART) ---
    chart_col1, chart_col2 = st.columns([3, 2])

    with chart_col1:
        st.subheader("🌊 Waterfall Analysis")
        if not filtered_df.empty and total_income + total_expenses > 0:
            expense_by_cat = filtered_df[filtered_df["Τύπος"] == "Έξοδο"].groupby("Κατηγορία")["Ποσό"].sum()
            x_list = ["INCOME"] + list(expense_by_cat.index) + ["BALANCE"]
            y_list = [total_income] + list(-expense_by_cat.values) + [0]
            measure_list = ["relative"] + ["relative"] * len(expense_by_cat) + ["total"]

            fig_waterfall = go.Figure(go.Waterfall(
                name="Cashflow", orientation="v",
                measure=measure_list, x=x_list, textposition="outside",
                text=[f"{val:.2f}" if val != 0 else f"{net_month:.2f}" for val in y_list[:-1]] + [f"{net_month:.2f}"],
                textfont=dict(color=chart_font_color, size=12),
                y=y_list,
                connector={"line": {"color": "rgb(63, 63, 63)"}},
                decreasing={"marker": {"color": "#EF553B"}},
                increasing={"marker": {"color": "#636EFA"}},
                totals={"marker": {"color": "#7F7F7F"}}
            ))
            fig_waterfall.update_layout(
                title=dict(text="Ανάλυση Ταμειακών Ροών", font=dict(color=chart_font_color)), 
                showlegend=False, 
                template=plotly_template, 
                paper_bgcolor=chart_bg,
                plot_bgcolor=chart_bg,
                font=dict(color=chart_font_color),
                height=400,
                xaxis=dict(fixedrange=True, color=chart_font_color, tickfont=dict(color=chart_font_color, size=12), gridcolor=chart_grid_color),
                yaxis=dict(fixedrange=True, color=chart_font_color, tickfont=dict(color=chart_font_color, size=12), gridcolor=chart_grid_color)
            )
            st.plotly_chart(fig_waterfall, use_container_width=True, config={'scrollZoom': False, 'displayModeBar': False})
        else:
            st.info("Δεν υπάρχουν δεδομένα για την εμφάνιση του Waterfall Chart.")

    with chart_col2:
        st.subheader("🍕 Κατανομή Εξόδων")
        if not filtered_df.empty and total_expenses > 0:
            exp_df = filtered_df[filtered_df["Τύπος"] == "Έξοδο"]
            fig_pie = px.pie(exp_df, values="Ποσό", names="Κατηγορία", hole=0.4, template=plotly_template)
            fig_pie.update_layout(
                height=400, 
                paper_bgcolor=chart_bg,
                plot_bgcolor=chart_bg,
                font=dict(color=chart_font_color),
                legend=dict(font=dict(color=chart_font_color)),
                xaxis=dict(fixedrange=True), 
                yaxis=dict(fixedrange=True)
            )
            fig_pie.update_traces(textfont=dict(color=chart_font_color))
            st.plotly_chart(fig_pie, use_container_width=True, config={'scrollZoom': False, 'displayModeBar': False})
        else:
            st.info("Δεν υπάρχουν έξοδα στη συγκεκριμένη περίοδο.")

    # --- LINE CHART: ΜΗΝΙΑΙΑ ΤΑΣΗ ---
    st.subheader("📈 Μηνιαία Τάση Εσόδων, Εξόδων & Καθαρού Υπολοίπου")
    if not df.empty:
        trend_df = df.copy()
        trend_df["dt"] = pd.to_datetime(trend_df["Ημερομηνία"], errors="coerce")
        trend_df = trend_df.dropna(subset=["dt"])
        trend_df["Sort_Key"] = trend_df["dt"].dt.strftime("%Y-%m")
        trend_df["Μήνας"] = trend_df["dt"].dt.strftime("%b %Y")
        
        monthly_summary = trend_df.groupby(["Sort_Key", "Μήνας", "Τύπος"])["Ποσό"].sum().reset_index()
        
        if not monthly_summary.empty:
            pivot_df = monthly_summary.pivot(index=["Sort_Key", "Μήνας"], columns="Τύπος", values="Ποσό").fillna(0.0).reset_index()
            if "Έσοδο" not in pivot_df.columns: pivot_df["Έσοδο"] = 0.0
            if "Έξοδο" not in pivot_df.columns: pivot_df["Έξοδο"] = 0.0
            pivot_df["Καθαρό (Net)"] = pivot_df["Έσοδο"] - pivot_df["Έξοδο"]
            
            pivot_df = pivot_df.sort_values("Sort_Key")

            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(x=pivot_df["Μήνας"], y=pivot_df["Έσοδο"], mode='lines+markers', name='Έσοδο', line=dict(color='#00CC96', width=3)))
            fig_line.add_trace(go.Scatter(x=pivot_df["Μήνας"], y=pivot_df["Έξοδο"], mode='lines+markers', name='Έξοδο', line=dict(color='#EF553B', width=3)))
            fig_line.add_trace(go.Scatter(x=pivot_df["Μήνας"], y=pivot_df["Καθαρό (Net)"], mode='lines+markers', name='Καθαρό (Net)', line=dict(color='#AB63FA', width=2, dash='dash')))

            fig_line.update_xaxes(type='category', fixedrange=True, color=chart_font_color, tickfont=dict(color=chart_font_color, size=12), title=dict(text="Μήνας", font=dict(color=chart_font_color)), gridcolor=chart_grid_color)
            fig_line.update_yaxes(fixedrange=True, color=chart_font_color, tickfont=dict(color=chart_font_color, size=12), title=dict(text="Ποσό (€)", font=dict(color=chart_font_color)), gridcolor=chart_grid_color)
            fig_line.update_layout(height=380, template=plotly_template, paper_bgcolor=chart_bg, plot_bgcolor=chart_bg, font=dict(color=chart_font_color), legend=dict(font=dict(color=chart_font_color)))
            st.plotly_chart(fig_line, use_container_width=True, config={'scrollZoom': False, 'displayModeBar': False})
    st.markdown("---")

    # --- TABLE, EDIT, DELETE & DOWNLOAD (MOBILE-FRIENDLY CARDS) ---
    st.subheader("📋 Ιστορικό Εγγραφών")

    if not filtered_df.empty:
        for idx, row in filtered_df.iterrows():
            with st.container(border=True):
                top_col1, top_col2 = st.columns([3, 1])
                with top_col1:
                    st.markdown(f"**{row['Ημερομηνία']}** | `{row['Κατηγορία']}`")
                    if row["Περιγραφή"]:
                        st.caption(f"📝 {row['Περιγραφή']}")
                with top_col2:
                    color = "#00CC96" if row["Τύπος"] == "Έσοδο" else "#EF553B"
                    st.markdown(f"<h4 style='text-align: right; color: {color}; margin:0;'>{row['Ποσό']:.2f} €</h4>", unsafe_allow_html=True)

                btn_col1, btn_col2, _ = st.columns([1, 1, 4])
                
                with btn_col1:
                    with st.popover("✏️"):
                        st.write(f"**Επεξεργασία (Γραμμή {int(idx)+2})**")
                        edit_date = st.date_input("Ημερομηνία", pd.to_datetime(row["Ημερομηνία"]), key=f"edit_date_{idx}")
                        edit_type = st.radio("Τύπος", ["Έσοδο", "Έξοδο"], index=0 if row["Τύπος"] == "Έσοδο" else 1, key=f"edit_type_{idx}")
                        edit_desc = st.text_input("Περιγραφή", value=row["Περιγραφή"], key=f"edit_desc_{idx}")
                        
                        cats = INCOME_CATEGORIES if edit_type == "Έσοδο" else EXPENSE_CATEGORIES
                        cat_index = cats.index(row["Κατηγορία"]) if row["Κατηγορία"] in cats else 0
                        edit_cat = st.selectbox("Κατηγορία", cats, index=cat_index, key=f"edit_cat_{idx}")
                        edit_amount = st.number_input("Ποσό (€)", value=float(row["Ποσό"]), min_value=0.0, format="%.2f", key=f"edit_amt_{idx}")

                        if st.button("Ενημέρωση", key=f"save_edit_{idx}"):
                            row_to_edit = int(idx) + 2
                            rec_state = row["Επαναλαμβανόμενο"] if "Επαναλαμβανόμενο" in row else "Όχι"
                            worksheet.update(f"A{row_to_edit}:F{row_to_edit}", [[str(edit_date), edit_desc, edit_type, edit_cat, edit_amount, rec_state]])
                            st.cache_data.clear()
                            st.success("Η εγγραφή ενημερώθηκε!")
                            st.rerun()

                with btn_col2:
                    with st.popover("🗑️"):
                        st.write("⚠️ **Επιβεβαίωση Διαγραφής;**")
                        st.caption(f"{row['Ημερομηνία']} | {row['Κατηγορία']} | {row['Ποσό']}€")
                        if st.button("Ναι, Διαγραφή!", key=f"confirm_del_{idx}", type="primary"):
                            row_to_delete = int(idx) + 2
                            worksheet.delete_rows(row_to_delete)
                            st.cache_data.clear()
                            st.success("Η εγγραφή διαγράφηκε!")
                            st.rerun()
    else:
        st.info("Δεν υπάρχουν εγγραφές για προβολή.")

    st.markdown("---")
    
    # Download Excel Report
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Data')
    excel_data = output.getvalue()

    st.download_button(
        label="📥 Download Excel Report",
        data=excel_data,
        file_name="finance_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # --- FOOTER ---
    st.markdown("<br><hr>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="text-align: center; color: #888888; font-size: 14px;">
            💻 <b>Personal Finance Tracker PRO</b> | Designed & Developed by <b>Σπύρος Βοϊκόπουλος</b> <br>
            ⚡ Powered by Streamlit & Google Sheets API
        </div>
        """,
        unsafe_allow_html=True
    )

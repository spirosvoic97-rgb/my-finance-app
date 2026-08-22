import streamlit as st
import pandas as pd
from config import ICON_URL, get_sheets_connection
from views_entry import render_entry
from views_dashboard import render_dashboard
from views_profile import render_profile
from views_chat import render_chat

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Personal Finance App",
    page_icon="💰",
    layout="wide"
)

# --- LOGIN / AUTHENTICATION LOGIC ---
def check_password():
    if st.session_state.get("password_correct", False):
        return True

    st.markdown("### 🔐 Σύνδεση στο Finance App")
    username_input = st.text_input("Όνομα Χρήστη (Username)", key="login_user")
    password_input = st.text_input("Κωδικός Πρόσβασης (Password)", type="password", key="login_pass")

    if st.button("Σύνδεση"):
        passwords = st.secrets.get("passwords", {})
        if username_input in passwords and passwords[username_input] == password_input:
            st.session_state["password_correct"] = True
            st.session_state["current_user"] = username_input
            st.rerun()
        else:
            st.error("❌ Λανθασμένο όνομα χρήστη ή κωδικός πρόσβασης.")

    return False

# --- HELPER: CALCULATE CURRENT BALANCE ---
def get_current_balance(worksheet, current_user):
    try:
        data = worksheet.get_all_values()
        if not data or len(data) <= 1:
            return 0.0
        
        raw_headers = data[0]
        clean_headers = [str(h).strip() if str(h).strip() else f"Col_{i+1}" for i, h in enumerate(raw_headers)]
        df = pd.DataFrame(data[1:], columns=clean_headers)

        if "Username" in df.columns:
            df = df[df["Username"] == current_user]

        if df.empty or "Ποσό" not in df.columns or "Τύπος" not in df.columns:
            return 0.0

        numeric_amounts = pd.to_numeric(df["Ποσό"].astype(str).str.replace(",", "."), errors="coerce").fillna(0.0)
        total_income = numeric_amounts[df["Τύπος"] == "Έσοδο"].sum()
        total_expense = numeric_amounts[df["Τύπος"] == "Έξοδο"].sum()
        
        return total_income - total_expense
    except Exception:
        return 0.0

# --- MAIN APP ROUTING ---
if check_password():
    current_user = st.session_state["current_user"]

    # Load Google Sheets connection
    try:
        worksheet, users_sheet = get_sheets_connection()
    except Exception as e:
        st.error(f"⚠️ Σφάλμα σύνδεσης με το Google Sheet: {e}")
        st.stop()

    # Calculate overall balance
    user_balance = get_current_balance(worksheet, current_user)

    # --- TOP HEADER WITH LOGO & ALWAYS-VISIBLE BALANCE ---
    col_logo, col_title, col_balance = st.columns([1, 5, 4])
    
    with col_logo:
        st.image(ICON_URL, width=55)
        
    with col_title:
        st.title("Personal Finance Tracker")
        st.caption(f"Χρήστης: **{current_user}**")
        
    with col_balance:
        st.metric(label="💳 Διαθέσιμο Υπόλοιπο", value=f"{user_balance:.2f} €")

    st.markdown("---")

    # --- APP NAVIGATION TABS ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "➕ Καταχώρηση", 
        "📊 Analytics", 
        "⚙️ Προφίλ", 
        "💬 AI Assistant"
    ])

    with tab1:
        render_entry(worksheet, current_user)

    with tab2:
        render_dashboard(worksheet, current_user)

    with tab3:
        render_profile(users_sheet, current_user)

    with tab4:
        render_chat(worksheet, current_user)

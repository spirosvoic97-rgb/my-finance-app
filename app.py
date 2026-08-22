import streamlit as st
from config import ICON_URL, get_sheets_connection
from views_entry import render_entry
from views_reports import render_reports
from views_settings import render_settings
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

# --- MAIN APP ROUTING ---
if check_password():
    current_user = st.session_state["current_user"]

    # Header section
    col_header1, col_header2 = st.columns([1, 8])
    with col_header1:
        st.image(ICON_URL, width=60)
    with col_header2:
        st.title("💰 Personal Finance Tracker")
        st.caption(f"Καλώς ήρθες, **{current_user}**!")

    # Load Google Sheets connection
    try:
        worksheet, users_sheet = get_sheets_connection()
    except Exception as e:
        st.error(f"⚠️ Σφάλμα σύνδεσης με το Google Sheet: {e}")
        st.stop()

    # --- APP NAVIGATION TABS ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "➕ Καταχώρηση", 
        "📊 Αναφορές", 
        "⚙️ Ρυθμίσεις", 
        "💬 AI Assistant"
    ])

    with tab1:
        render_entry(worksheet, current_user)

    with tab2:
        render_reports(worksheet, current_user)

    with tab3:
        render_settings(users_sheet, current_user)

    with tab4:
        render_chat(worksheet, current_user)

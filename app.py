import streamlit as st
import pandas as pd
from config import ICON_URL, get_sheets_connection
from views_entry import render_entry
from views_dashboard import render_dashboard
from views_profile import render_profile
from views_chat import render_chat

st.set_page_config(
    page_title="Personal Finance App",
    page_icon="💰",
    layout="wide"
)

# --- LOGIN & SIGNUP WITH EMAIL AUTHENTICATION ---
def check_password(users_sheet):
    if st.session_state.get("password_correct", False):
        return True

    tab_login, tab_signup = st.tabs(["🔐 Σύνδεση", "📝 Εγγραφή Νέου Χρήστη"])

    # LOGIN TAB
    with tab_login:
        st.markdown("### 🔐 Σύνδεση στο Finance App")
        st.caption("Συνδέσου με το Email σου για ταυτόχρονη πρόσβαση από όλες τις συσκευές σου.")
        email_input = st.text_input("Email Χρήστη", key="login_email").strip().lower()
        password_input = st.text_input("Κωδικός Πρόσβασης (Password)", type="password", key="login_pass")

        if st.button("Σύνδεση", key="btn_login"):
            passwords = st.secrets.get("passwords", {})
            
            # Διάβασμα χρηστών από το Google Sheet (Email -> Password, Username)
            sheet_users = {}
            try:
                u_data = users_sheet.get_all_values()
                if len(u_data) > 1:
                    # Αναμενόμενη δομή Sheet Χρηστών: Email | Password | Username
                    for row in u_data[1:]:
                        if len(row) >= 2:
                            em = str(row[0]).strip().lower()
                            pw = str(row[1]).strip()
                            uname = str(row[2]).strip() if len(row) >= 3 else em.split("@")[0]
                            sheet_users[em] = {"pass": pw, "username": uname}
            except Exception:
                pass

            # Έλεγχος στα Secrets
            if email_input in passwords and passwords[email_input] == password_input:
                st.session_state["password_correct"] = True
                st.session_state["current_user"] = email_input.split("@")[0]
                st.session_state["user_email"] = email_input
                st.rerun()
            # Έλεγχος στο Google Sheet
            elif email_input in sheet_users and sheet_users[email_input]["pass"] == password_input:
                st.session_state["password_correct"] = True
                st.session_state["current_user"] = sheet_users[email_input]["username"]
                st.session_state["user_email"] = email_input
                st.rerun()
            else:
                st.error("❌ Λανθασμένο Email ή Κωδικός Πρόσβασης.")

    # SIGNUP TAB
    with tab_signup:
        st.markdown("### 📝 Δημιουργία Νέου Λογαριασμού")
        st.caption("Το Email σου θα χρησιμοποιηθεί για τον συγχρονισμό μεταξύ των συσκευών σου.")
        new_email = st.text_input("Email", key="signup_email").strip().lower()
        new_user = st.text_input("Όνομα / Username (π.χ. spiros)", key="signup_user").strip()
        new_pass = st.text_input("Νέος Κωδικός", type="password", key="signup_pass")
        confirm_pass = st.text_input("Επιβεβαίωση Κωδικού", type="password", key="signup_confirm")

        if st.button("Δημιουργία Λογαριασμού", key="btn_signup"):
            if not new_email or not new_user or not new_pass:
                st.warning("⚠️ Παρακαλώ συμπληρώστε όλα τα πεδία.")
            elif "@" not in new_email or "." not in new_email:
                st.error("❌ Παρακαλώ εισάγετε ένα έγκυρο Email.")
            elif new_pass != confirm_pass:
                st.error("❌ Οι κωδικοί δεν ταιριάζουν.")
            else:
                try:
                    # Αποθήκευση στο Sheet: Email, Password, Username
                    users_sheet.append_row([new_email, new_pass, new_user], value_input_option="USER_ENTERED")
                    st.success("🎉 Ο λογαριασμός δημιουργήθηκε επιτυχώς! Μπορείτε τώρα να συνδεθείτε από οποιαδήποτε συσκευή.")
                except Exception as e:
                    st.error(f"⚠️ Σφάλμα κατά την εγγραφή: {e}")

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
try:
    worksheet, users_sheet = get_sheets_connection()
except Exception as e:
    st.error(f"⚠️ Σφάλμα σύνδεσης με το Google Sheet: {e}")
    st.stop()

if check_password(users_sheet):
    current_user = st.session_state["current_user"]
    user_email = st.session_state.get("user_email", "")
    user_balance = get_current_balance(worksheet, current_user)

    col_logo, col_title, col_balance = st.columns([1, 5, 4])
    
    with col_logo:
        st.image(ICON_URL, width=55)
        
    with col_title:
        st.title("Personal Finance Tracker")
        st.caption(f"Χρήστης: **{current_user}** ({user_email})")
        
    with col_balance:
        st.metric(label="💳 Διαθέσιμο Υπόλοιπο", value=f"{user_balance:.2f} €")

    st.markdown("---")

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

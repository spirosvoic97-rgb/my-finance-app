import streamlit as st
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import bcrypt
import string
import random
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

# --- HELPER: PASSWORD STRENGTH CHECKER ---
def is_strong_password(password):
    """Ελέγχει αν ο κωδικός πληροί τους αυστηρούς κανόνες ασφαλείας."""
    if len(password) < 8:
        return False, "Ο κωδικός πρέπει να έχει τουλάχιστον 8 χαρακτήρες."
    if not any(c.isupper() for c in password):
        return False, "Ο κωδικός πρέπει να περιέχει τουλάχιστον 1 κεφαλαίο γράμμα."
    if not any(c.isdigit() for c in password):
        return False, "Ο κωδικός πρέπει να περιέχει τουλάχιστον 1 αριθμό."
    if not any(c in string.punctuation for c in password):
        return False, f"Ο κωδικός πρέπει να περιέχει τουλάχιστον 1 ειδικό σύμβολο (π.χ. @, #, $, %, !)."
    return True, ""

# --- HELPER: EMAIL SENDER FOR PASSWORD RESET ---
def send_email(to_email, subject, body):
    if "email" not in st.secrets:
        return False, "Δεν έχουν ρυθμιστεί τα Email Secrets."
    try:
        conf = st.secrets["email"]
        msg = MIMEText(body, "html", "utf-8")
        msg["Subject"] = subject
        msg["From"] = conf["sender_email"]
        msg["To"] = to_email

        server = smtplib.SMTP(conf["smtp_server"], int(conf["smtp_port"]))
        server.starttls()
        server.login(conf["sender_email"], conf["sender_password"])
        server.send_message(msg)
        server.quit()
        return True, "Το email στάλθηκε επιτυχώς!"
    except Exception as e:
        return False, f"Σφάλμα αποστολής: {e}"

# --- LOGIN & SIGNUP AUTHENTICATION LOGIC ---
def check_password(users_sheet):
    if st.session_state.get("password_correct", False):
        return True

    tab_login, tab_signup, tab_reset = st.tabs(["🔐 Σύνδεση", "📝 Εγγραφή Νέου Χρήστη", "🔑 Ανάκτηση Κωδικού"])

    # LOGIN TAB
    with tab_login:
        st.markdown("### 🔐 Σύνδεση στο Finance App")
        username_input = st.text_input("Όνομα Χρήστη (Username)", key="login_user").strip()
        password_input = st.text_input("Κωδικός Πρόσβασης (Password)", type="password", key="login_pass")

        if st.button("Σύνδεση", key="btn_login"):
            sheet_users = {}
            try:
                u_data = users_sheet.get_all_values()
                if len(u_data) > 1:
                    for row in u_data[1:]:
                        if len(row) >= 3:
                            em = str(row[0]).strip().lower()
                            pw = str(row[1]).strip()
                            uname = str(row[2]).strip()
                            sheet_users[uname] = {"pass": pw, "email": em}
            except Exception:
                pass

            if username_input in sheet_users:
                stored_hash = sheet_users[username_input]["pass"]
                try:
                    if bcrypt.checkpw(password_input.encode('utf-8'), stored_hash.encode('utf-8')):
                        st.session_state["password_correct"] = True
                        st.session_state["current_user"] = username_input
                        st.session_state["user_email"] = sheet_users[username_input]["email"]
                        st.rerun()
                    else:
                        st.error("❌ Λανθασμένος Κωδικός Πρόσβασης.")
                except ValueError:
                    st.error("❌ Βρέθηκε παλιός, μη κρυπτογραφημένος κωδικός. Διαγράψτε τον χρήστη από το Excel και κάντε νέα εγγραφή.")
            else:
                st.error("❌ Δεν βρέθηκε χρήστης με αυτό το όνομα.")

    # SIGNUP TAB
    with tab_signup:
        st.markdown("### 📝 Δημιουργία Νέου Λογαριασμού")
        new_email = st.text_input("Email", key="signup_email").strip().lower()
        new_user = st.text_input("Όνομα Χρήστη (Username)", key="signup_user").strip()
        new_pass = st.text_input("Νέος Κωδικός", type="password", key="signup_pass")
        confirm_pass = st.text_input("Επιβεβαίωση Κωδικού", type="password", key="signup_confirm")
        
        st.caption("Ο κωδικός πρέπει να έχει: τουλ. 8 χαρακτήρες, 1 κεφαλαίο, 1 αριθμό, 1 σύμβολο.")

        if st.button("Δημιουργία Λογαριασμού", key="btn_signup"):
            if not new_email or not new_user or not new_pass:
                st.warning("⚠️ Παρακαλώ συμπληρώστε όλα τα πεδία.")
            elif "@" not in new_email or "." not in new_email:
                st.error("❌ Παρακαλώ εισάγετε ένα έγκυρο Email.")
            elif new_pass != confirm_pass:
                st.error("❌ Οι κωδικοί δεν ταιριάζουν.")
            else:
                # --- ΕΔΩ ΕΙΝΑΙ Ο ΝΕΟΣ ΑΥΣΤΗΡΟΣ ΕΛΕΓΧΟΣ ---
                is_valid, error_message = is_strong_password(new_pass)
                
                if not is_valid:
                    st.error(f"❌ {error_message}")
                else:
                    try:
                        # Κρυπτογράφηση του νέου κωδικού (Hashing)
                        hashed_pw = bcrypt.hashpw(new_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                        users_sheet.append_row([new_email, hashed_pw, new_user], value_input_option="USER_ENTERED")
                        st.success(f"🎉 Ο λογαριασμός για τον χρήστη '{new_user}' δημιουργήθηκε επιτυχώς! Μπορείτε τώρα να συνδεθείτε.")
                    except Exception as e:
                        st.error(f"⚠️ Σφάλμα κατά την εγγραφή: {e}")

    # RESET PASSWORD TAB
    with tab_reset:
        st.markdown("### 🔑 Ανάκτηση Κωδικού")
        reset_email = st.text_input("Εισάγετε το Email σας", key="reset_email").strip().lower()

        if st.button("Αποστολή Προσωρινού Κωδικού", key="btn_reset"):
            if not reset_email:
                st.warning("⚠️ Παρακαλώ συμπληρώστε το email σας.")
            else:
                try:
                    u_data = users_sheet.get_all_values()
                    found_user, found_row_index = None, None
                    if len(u_data) > 1:
                        for i, row in enumerate(u_data[1:], start=2):
                            if len(row) >= 3 and str(row[0]).strip().lower() == reset_email:
                                found_user = row[2]
                                found_row_index = i
                                break

                    if found_row_index:
                        temp_pass = ''.join(random.choices(string.ascii_letters + string.digits, k=8)) + "A1!"
                        temp_hashed = bcrypt.hashpw(temp_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                        
                        users_sheet.update_cell(found_row_index, 2, temp_hashed)

                        subject = "🔑 Νέος Κωδικός - Personal Finance Tracker"
                        body = f"""
                        <h3>Γεια σου {found_user},</h3>
                        <p>Ζητήθηκε ανάκτηση κωδικού για την εφαρμογή. Ορίστηκε ένας προσωρινός κωδικός.</p>
                        <p><b>Username:</b> {found_user}<br>
                        <b>Προσωρινός Κωδικός:</b> <code>{temp_pass}</code></p>
                        <hr>
                        <p><small>Συνδεθείτε με αυτόν τον κωδικό.</small></p>
                        """
                        ok, msg = send_email(reset_email, subject, body)
                        if ok:
                            st.success("✅ Ο νέος κωδικός σας στάλθηκε στο email σας!")
                        else:
                            st.error(f"⚠️ {msg}")
                    else:
                        st.error("❌ Δεν βρέθηκε λογαριασμός με αυτό το email.")
                except Exception as e:
                    st.error(f"⚠️ Σφάλμα: {e}")

    return False

# --- HELPER: CALCULATE CURRENT BALANCE ---
@st.cache_data(ttl=600)
def get_cached_sheet_data(_worksheet):
    return _worksheet.get_all_values()

def get_current_balance(worksheet, current_user):
    try:
        data = get_cached_sheet_data(worksheet)
        if not data or len(data) <= 1: return 0.0
        
        raw_headers = data[0]
        clean_headers = [str(h).strip() if str(h).strip() else f"Col_{i+1}" for i, h in enumerate(raw_headers)]
        df = pd.DataFrame(data[1:], columns=clean_headers)

        if "Username" in df.columns: df = df[df["Username"] == current_user]
        if df.empty or "Ποσό" not in df.columns or "Τύπος" not in df.columns: return 0.0

        numeric_amounts = pd.to_numeric(df["Ποσό"].astype(str).str.replace(",", "."), errors="coerce").fillna(0.0)
        total_income = numeric_amounts[df["Τύπος"] == "Έσοδο"].sum()
        total_expense = numeric_amounts[df["Τύπος"] == "Έξοδο"].sum()
        return total_income - total_expense
    except Exception as e:
        st.error(f"Σφάλμα υπολογισμού υπολοίπου: {e}")
        return 0.0

# --- MAIN APP ROUTING ---
try:
    worksheet, users_sheet = get_sheets_connection()
except Exception as e:
    st.error(f"⚠️ Σφάλμα σύνδεσης: {e}")
    st.stop()

if check_password(users_sheet):
    current_user = st.session_state["current_user"]
    user_email = st.session_state.get("user_email", "")
    user_balance = get_current_balance(worksheet, current_user)

    col_logo, col_title, col_balance = st.columns([1, 5, 4])
    with col_logo: st.image(ICON_URL, width=55)
    with col_title:
        st.title("Personal Finance Tracker")
        st.caption(f"Χρήστης: **{current_user}**" + (f" ({user_email})" if user_email else ""))
    with col_balance: st.metric(label="💳 Διαθέσιμο Υπόλοιπο", value=f"{user_balance:.2f} €")
    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs(["➕ Καταχώρηση", "📊 Analytics", "⚙️ Προφίλ", "💬 AI Assistant"])
    with tab1: render_entry(worksheet, current_user)
    with tab2: render_dashboard(worksheet, current_user)
    with tab3: render_profile(users_sheet, worksheet, current_user)
    with tab4: render_chat(worksheet, current_user)

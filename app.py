import streamlit as st
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import bcrypt
import string
import random
from config import get_sheets_connection
from views_entry import render_entry
from views_dashboard import render_dashboard
from views_profile import render_profile
from views_chat import render_chat

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Personal Finance App",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS INJECTION: HIDE TOOLBAR BUT KEEP SIDEBAR TOGGLE ---
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .stDeployButton {display:none;}
        div[data-testid="stDecoration"] {display:none;}
        div[data-testid="stStatusWidget"] {visibility: hidden !important;}
        
        button[data-testid="stSidebarCollapseButton"] {
            visibility: visible !important;
            display: block !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- TRANSLATIONS (i18n) ---
TRANSLATIONS = {
    "EL": {
        "login_title": "🔐 Σύνδεση",
        "signup_title": "📝 Δημιουργία Λογαριασμού",
        "reset_title": "🔑 Ανάκτηση Κωδικού",
        "username": "Όνομα Χρήστη",
        "password": "Κωδικός Πρόσβασης",
        "confirm_pass": "Επιβεβαίωση Κωδικού",
        "email": "Email",
        "login_btn": "Σύνδεση",
        "signup_btn": "Δημιουργία Λογαριασμού",
        "reset_btn": "Αποστολή Προσωρινού Κωδικού",
        "no_account": "Δεν έχεις λογαριασμό; Εγγραφή",
        "have_account": "Έχεις ήδη λογαριασμό; Σύνδεση",
        "forgot_pass": "Ξέχασες τον κωδικό σου;",
        "pass_rules": "Ο κωδικός πρέπει να έχει: τουλ. 8 χαρακτήρες, 1 κεφαλαίο, 1 αριθμό, 1 σύμβολο.",
        "fill_all": "⚠️ Συμπληρώστε όλα τα πεδία.",
        "invalid_email": "❌ Παρακαλώ εισάγετε ένα έγκυρο Email.",
        "pass_mismatch": "❌ Οι κωδικοί δεν ταιριάζουν.",
        "signup_success": "🎉 Ο λογαριασμός δημιουργήθηκε επιτυχώς! Μπορείτε να συνδεθείτε.",
        "wrong_pass": "❌ Λανθασμένος Κωδικός Πρόσβασης.",
        "user_not_found": "❌ Δεν βρέθηκε χρήστης με αυτό το όνομα.",
        "reset_sent": "✅ Ο νέος κωδικός στάλθηκε στο email σας!",
        "nav_entry": "➕ Καταχώρηση",
        "nav_analytics": "📊 Analytics",
        "nav_ai": "💬 AI Assistant",
        "balance": "💳 Διαθέσιμο Υπόλοιπο",
        "welcome": "Καλώς ήρθες",
        "settings": "⚙️ Ρυθμίσεις & Προφίλ",
        "back_to_app": "⬅️ Επιστροφή στην Εφαρμογή",
        "logout": "🚪 Αποσύνδεση",
        "language": "🌐 Γλώσσα / Language",
        "dash_title": "📊 Αναφορές & Analytics",
        "dash_no_data": "Δεν υπάρχουν καταχωρημένα δεδομένα.",
        "dash_no_data_user": "Δεν βρέθηκαν εγγραφές για τον χρήστη.",
        "dash_filters": "📅 Φίλτρα Χρονικής Περιόδου",
        "dash_year": "Επιλογή Έτους",
        "dash_month": "Επιλογή Μήνα",
        "dash_inc": "💰 Έσοδα Περιόδου",
        "dash_exp": "💸 Έξοδα Περιόδου",
        "dash_net": "📈 Καθαρό Αποτέλεσμα",
        "dash_pie_title": "🍩 Κατανομή Εξόδων ανά Κατηγορία",
        "dash_bar_title": "📊 Μηνιαία Τάση Εσόδων vs Εξόδων",
        "dash_no_exp": "Δεν υπάρχουν έξοδα για τη συγκεκριμένη περίοδο.",
        "dash_no_trend": "Δεν υπάρχουν δεδομένα τάσης.",
        "inc_label": "Έσοδα",
        "exp_label": "Έξοδοι",
        "all": "Όλα",
        "month": "Μήνας"
    },
    "EN": {
        "login_title": "🔐 Login",
        "signup_title": "📝 Create Account",
        "reset_title": "🔑 Password Recovery",
        "username": "Username",
        "password": "Password",
        "confirm_pass": "Confirm Password",
        "email": "Email",
        "login_btn": "Login",
        "signup_btn": "Create Account",
        "reset_btn": "Send Temp Password",
        "no_account": "Don't have an account? Sign Up",
        "have_account": "Already have an account? Login",
        "forgot_pass": "Forgot password?",
        "pass_rules": "Min 8 chars, 1 uppercase, 1 number, 1 symbol.",
        "fill_all": "⚠️ Please fill in all fields.",
        "invalid_email": "❌ Please enter a valid Email.",
        "pass_mismatch": "❌ Passwords do not match.",
        "signup_success": "🎉 Account created successfully! You can now login.",
        "wrong_pass": "❌ Incorrect Password.",
        "user_not_found": "❌ User not found.",
        "reset_sent": "✅ Temporary password sent to email!",
        "nav_entry": "➕ Entries",
        "nav_analytics": "📊 Analytics",
        "nav_ai": "💬 AI Assistant",
        "balance": "💳 Available Balance",
        "welcome": "Welcome back",
        "settings": "⚙️ Settings & Profile",
        "back_to_app": "⬅️ Back to Main App",
        "logout": "🚪 Logout",
        "language": "🌐 Language",
        "dash_title": "📊 Reports & Analytics",
        "dash_no_data": "No recorded data found.",
        "dash_no_data_user": "No entries found for this user.",
        "dash_filters": "📅 Date Filters",
        "dash_year": "Select Year",
        "dash_month": "Select Month",
        "dash_inc": "💰 Period Income",
        "dash_exp": "💸 Period Expenses",
        "dash_net": "📈 Net Result",
        "dash_pie_title": "🍩 Expense Distribution by Category",
        "dash_bar_title": "📊 Monthly Income vs Expense Trend",
        "dash_no_exp": "No expenses found for this period.",
        "dash_no_trend": "No trend data available.",
        "inc_label": "Income",
        "exp_label": "Expenses",
        "all": "All",
        "month": "Month"
    }
}

# --- STATE INITIALIZATION ---
if "lang" not in st.session_state:
    st.session_state["lang"] = "EL"
if "view_mode" not in st.session_state:
    st.session_state["view_mode"] = "main"

t = TRANSLATIONS[st.session_state["lang"]]

# --- HELPER: PASSWORD STRENGTH CHECKER ---
def is_strong_password(password):
    if len(password) < 8:
        return False, "Min 8 characters."
    if not any(c.isupper() for c in password):
        return False, "At least 1 uppercase letter."
    if not any(c.isdigit() for c in password):
        return False, "At least 1 number."
    if not any(c in string.punctuation for c in password):
        return False, "At least 1 symbol."
    return True, ""

# --- HELPER: EMAIL SENDER FOR PASSWORD RESET ---
def send_email(to_email, subject, body):
    if "email" not in st.secrets:
        return False, "Missing Email Secrets."
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
        return True, "Email sent successfully!"
    except Exception as e:
        return False, f"Email error: {e}"

# --- AUTHENTICATION SCREEN LOGIC ---
def check_password(users_sheet):
    if st.session_state.get("password_correct", False):
        return True

    if "auth_mode" not in st.session_state:
        st.session_state["auth_mode"] = "login"

    col_space, col_lang = st.columns([5, 1])
    with col_lang:
        selected_lang = st.selectbox("🌐", ["EL", "EN"], index=0 if st.session_state["lang"] == "EL" else 1, key="auth_lang_select")
        if selected_lang != st.session_state["lang"]:
            st.session_state["lang"] = selected_lang
            st.rerun()

    t = TRANSLATIONS[st.session_state["lang"]]

    col_main, _ = st.columns([2, 1])
    with col_main:
        if st.session_state["auth_mode"] == "login":
            st.markdown(f"### {t['login_title']}")
            with st.form(key="login_form"):
                username_input = st.text_input(t["username"]).strip()
                password_input = st.text_input(t["password"], type="password")
                submit_login = st.form_submit_button(t["login_btn"])

                if submit_login:
                    if not username_input or not password_input:
                        st.warning(t["fill_all"])
                    else:
                        sheet_users = {}
                        try:
                            u_data = users_sheet.get_all_values()
                            if len(u_data) > 1:
                                for row in u_data[1:]:
                                    if len(row) >= 3:
                                        sheet_users[str(row[2]).strip()] = {
                                            "pass": str(row[1]).strip(),
                                            "email": str(row[0]).strip().lower()
                                        }
                        except Exception:
                            pass

                        if username_input in sheet_users:
                            stored_hash = sheet_users[username_input]["pass"]
                            try:
                                if bcrypt.checkpw(password_input.encode('utf-8'), stored_hash.encode('utf-8')):
                                    st.session_state["password_correct"] = True
                                    st.session_state["current_user"] = username_input
                                    st.session_state["user_email"] = sheet_users[username_input]["email"]
                                    st.session_state["view_mode"] = "main"
                                    st.rerun()
                                else:
                                    st.error(t["wrong_pass"])
                            except ValueError:
                                st.error("❌ Legacy plain-text password found. Delete user from Sheet and re-register.")
                        else:
                            st.error(t["user_not_found"])

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button(t["no_account"], key="goto_signup"):
                    st.session_state["auth_mode"] = "signup"
                    st.rerun()
            with col_btn2:
                if st.button(t["forgot_pass"], key="goto_reset"):
                    st.session_state["auth_mode"] = "reset"
                    st.rerun()

        elif st.session_state["auth_mode"] == "signup":
            st.markdown(f"### {t['signup_title']}")
            with st.form(key="signup_form"):
                new_email = st.text_input(t["email"]).strip().lower()
                new_user = st.text_input(t["username"]).strip()
                new_pass = st.text_input(t["password"], type="password")
                confirm_pass = st.text_input(t["confirm_pass"], type="password")
                st.caption(t["pass_rules"])

                submit_signup = st.form_submit_button(t["signup_btn"])

                if submit_signup:
                    if not new_email or not new_user or not new_pass or not confirm_pass:
                        st.warning(t["fill_all"])
                    elif "@" not in new_email or "." not in new_email:
                        st.error(t["invalid_email"])
                    elif new_pass != confirm_pass:
                        st.error(t["pass_mismatch"])
                    else:
                        is_valid, error_msg = is_strong_password(new_pass)
                        if not is_valid:
                            st.error(f"❌ {error_msg}")
                        else:
                            try:
                                hashed_pw = bcrypt.hashpw(new_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                                users_sheet.append_row([new_email, hashed_pw, new_user], value_input_option="USER_ENTERED")
                                st.success(t["signup_success"])
                                st.session_state["auth_mode"] = "login"
                            except Exception as e:
                                st.error(f"⚠️ Error: {e}")

            if st.button(t["have_account"], key="goto_login_from_signup"):
                st.session_state["auth_mode"] = "login"
                st.rerun()

        elif st.session_state["auth_mode"] == "reset":
            st.markdown(f"### {t['reset_title']}")
            with st.form(key="reset_form"):
                reset_email = st.text_input(t["email"]).strip().lower()
                submit_reset = st.form_submit_button(t["reset_btn"])

                if submit_reset:
                    if not reset_email:
                        st.warning(t["fill_all"])
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

                                subject = "🔑 Reset Password - Personal Finance Tracker"
                                body = f"<h3>Hello {found_user},</h3><p>Your temp password is: <code>{temp_pass}</code></p>"
                                ok, msg = send_email(reset_email, subject, body)
                                if ok:
                                    st.success(t["reset_sent"])
                                    st.session_state["auth_mode"] = "login"
                                else:
                                    st.error(f"⚠️ {msg}")
                            else:
                                st.error("❌ Email not found.")
                        except Exception as e:
                            st.error(f"⚠️ Error: {e}")

            if st.button(t["have_account"], key="goto_login_from_reset"):
                st.session_state["auth_mode"] = "login"
                st.rerun()

    return False

# --- HELPER: BALANCE CALCULATOR ---
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
    except Exception:
        return 0.0

# --- MAIN APP ROUTING ---
try:
    worksheet, users_sheet = get_sheets_connection()
except Exception as e:
    st.error(f"⚠️ Connection Error: {e}")
    st.stop()

if check_password(users_sheet):
    current_user = st.session_state["current_user"]
    user_balance = get_current_balance(worksheet, current_user)
    t = TRANSLATIONS[st.session_state["lang"]]

    # --- SIDEBAR MENU ---
    with st.sidebar:
        st.title(f"👤 {current_user}")
        st.markdown("---")
        
        selected_lang = st.selectbox(t["language"], ["EL", "EN"], index=0 if st.session_state["lang"] == "EL" else 1, key="sidebar_lang")
        if selected_lang != st.session_state["lang"]:
            st.session_state["lang"] = selected_lang
            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.session_state["view_mode"] == "main":
            if st.button(t["settings"], use_container_width=True, key="btn_open_profile"):
                st.session_state["view_mode"] = "profile"
                st.rerun()

        st.markdown("---")
        if st.button(t["logout"], use_container_width=True):
            st.session_state["password_correct"] = False
            st.session_state["current_user"] = None
            st.session_state["view_mode"] = "main"
            st.rerun()

    # --- MAIN VIEW SWITCHING ---
    if st.session_state["view_mode"] == "profile":
        if st.button(t["back_to_app"], key="btn_top_back"):
            st.session_state["view_mode"] = "main"
            st.rerun()
            
        st.markdown("---")
        st.subheader(t["settings"])
        render_profile(users_sheet, worksheet, current_user, t)
    else:
        col_title, col_balance = st.columns([5, 3])
        with col_title:
            st.title("Personal Finance Tracker")
            st.caption(f"{t['welcome']}, **{current_user}** 👋")
        with col_balance: 
            st.metric(label=t["balance"], value=f"{user_balance:.2f} €")
            
        st.markdown("---")

        tab1, tab2, tab3 = st.tabs([t["nav_entry"], t["nav_analytics"], t["nav_ai"]])
        with tab1: render_entry(worksheet, current_user, t)
        with tab2: render_dashboard(worksheet, current_user, t)
        with tab3: render_chat(worksheet, current_user, t)

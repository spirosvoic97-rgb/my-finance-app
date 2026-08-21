import streamlit as st
import hashlib
import datetime

def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hash(password, hashed_text):
    return make_hash(password) == hashed_text

def render_login_signup(users_sheet):
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.title("🔒 FinancePRO")
        tab_login, tab_signup = st.tabs(["🔑 Σύνδεση", "📝 Εγγραφή Νέου Χρήστη"])
        
        with tab_login:
            col1, _ = st.columns([1, 2])
            with col1:
                username = st.text_input("Χρήστης", key="login_user")
                password = st.text_input("Κωδικός", type="password", key="login_pass")
                if st.button("Σύνδεση", key="login_btn"):
                    secrets_valid = False
                    if "passwords" in st.secrets and username.strip() in st.secrets["passwords"]:
                        if password == st.secrets["passwords"][username.strip()]:
                            secrets_valid = True

                    sheet_valid = False
                    user_email = ""
                    user_starting_bal = 0.00
                    try:
                        users_data = users_sheet.get_all_records()
                        for u in users_data:
                            if str(u.get("Username", "")).strip().lower() == username.strip().lower() and check_hash(password, str(u.get("PasswordHash", ""))):
                                sheet_valid = True
                                user_email = str(u.get("Email", ""))
                                try:
                                    user_starting_bal = float(u.get("StartingBalance", 0.00))
                                except Exception:
                                    user_starting_bal = 0.00
                                break
                    except Exception:
                        pass

                    if secrets_valid or sheet_valid:
                        st.session_state["authenticated"] = True
                        st.session_state["current_user"] = username.strip()
                        st.session_state["user_email"] = user_email
                        st.session_state["starting_balance"] = user_starting_bal
                        st.session_state["theme"] = "Dark Mode 🌙"
                        st.success("✅ Επιτυχής σύνδεση!")
                        st.rerun()
                    else:
                        st.error("❌ Λάθος όνομα χρήστη ή κωδικός πρόσβασης")
                        
        with tab_signup:
            col1, _ = st.columns([1, 2])
            with col1:
                new_username = st.text_input("Νέο Όνομα Χρήστη", key="signup_user")
                new_email = st.text_input("Email (Προαιρετικό)", key="signup_email")
                init_bal = st.number_input("Αρχικό Ταμείο (€)", value=0.00, step=50.00, key="signup_init_bal")
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
                        existing_users = []
                        try:
                            users_data = users_sheet.get_all_records()
                            existing_users = [str(u.get("Username", "")).strip().lower() for u in users_data]
                        except Exception:
                            pass

                        if new_username.strip().lower() in existing_users:
                            st.error("❌ Το όνομα χρήστη υπάρχει ήδη! Διάλεξε άλλο.")
                        else:
                            pass_hash = make_hash(new_password)
                            created_at = str(datetime.date.today())
                            users_sheet.append_row([new_username.strip(), pass_hash, created_at, new_email, float(init_bal)])
                            st.success("🎉 Ο λογαριασμός δημιουργήθηκε επιτυχώς! Μπορείς τώρα να συνδεθείς.")
        return False
    return True

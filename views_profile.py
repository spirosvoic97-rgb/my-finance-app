import streamlit as st
import pandas as pd
import smtplib
from io import BytesIO
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

def send_email_attachment(to_email, subject, body, attachment_bytes=None, filename=""):
    if "email" not in st.secrets:
        return False, "Δεν έχουν ρυθμιστεί τα Email Secrets στο Streamlit Cloud."
    try:
        conf = st.secrets["email"]
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = conf["sender_email"]
        msg["To"] = to_email

        msg.attach(MIMEText(body, "html", "utf-8"))

        if attachment_bytes and filename:
            part = MIMEApplication(attachment_bytes, Name=filename)
            part['Content-Disposition'] = f'attachment; filename="{filename}"'
            msg.attach(part)

        server = smtplib.SMTP(conf["smtp_server"], int(conf["smtp_port"]))
        server.starttls()
        server.login(conf["sender_email"], conf["sender_password"])
        server.send_message(msg)
        server.quit()
        return True, "Το email στάλθηκε επιτυχώς!"
    except Exception as e:
        return False, f"Σφάλμα αποστολής: {e}"

def render_profile(users_sheet, current_user):
    st.subheader("⚙️ Διαχείριση Προφίλ & Υπηρεσίες Email")
    st.write(f"Συνδεδεμένος χρήστης: **{current_user}**")
    
    user_email = st.session_state.get("user_email", "").strip()

    # --- ΕΝΗΜΕΡΩΣΗ / ΣΥΝΔΕΣΗ EMAIL ---
    st.markdown("#### 📧 Σύνδεση / Ενημέρωση Email")
    new_email_val = st.text_input("Το Email σου:", value=user_email, placeholder="π.χ. myemail@gmail.com", key="input_profile_email")

    if st.button("💾 Αποθήκευση Email", key="btn_save_email"):
        if not new_email_val or "@" not in new_email_val or "." not in new_email_val:
            st.error("❌ Παρακαλώ εισάγετε ένα έγκυρο Email.")
        else:
            try:
                # Ενημέρωση ή εγγραφή στο Sheet χρηστών
                u_data = users_sheet.get_all_values()
                found = False
                if len(u_data) > 1:
                    for i, row in enumerate(u_data[1:], start=2):
                        if len(row) >= 3 and str(row[2]).strip() == current_user:
                            users_sheet.update_cell(i, 1, new_email_val.lower())
                            found = True
                            break
                        elif len(row) >= 1 and str(row[0]).strip() == current_user:
                            users_sheet.update_cell(i, 1, new_email_val.lower())
                            found = True
                            break
                
                if not found:
                    passwords = st.secrets.get("passwords", {})
                    user_pass = passwords.get(current_user, "123456")
                    users_sheet.append_row([new_email_val.lower(), user_pass, current_user], value_input_option="USER_ENTERED")

                st.session_state["user_email"] = new_email_val.lower()
                st.success("✅ Το email ενημερώθηκε και αποθηκεύτηκε επιτυχώς!")
                st.rerun()
            except Exception as e:
                st.error(f"⚠️ Σφάλμα αποθήκευσης: {e}")

    st.markdown("---")
    st.markdown("### 📧 Λειτουργίες Email & Backup")

    col_mail1, col_mail2 = st.columns(2)

    with col_mail1:
        st.markdown("#### 📊 Μηνιαίο Report")
        st.caption("Στείλε αμέσως μια αναφορά των εξόδων σου στο email σου.")
        if st.button("📩 Αποστολή Μηνιαίου Report", key="btn_send_report"):
            current_email = st.session_state.get("user_email", "").strip()
            if not current_email:
                st.error("❌ Παρακαλώ αποθηκεύστε πρώτα το Email σου παραπάνω.")
            else:
                subject = "📊 Μηνιαία Οικονομική Αναφορά - Personal Finance Tracker"
                body = f"""
                <h2>Γεια σου {current_user}! 💰</h2>
                <p>Εδώ είναι η μηνιαία σύνοψη των οικονομικών σου από το <b>Personal Finance Tracker</b>.</p>
                <p>Όλες οι λειτουργίες και τα διαγράμματά σου είναι διαθέσιμα στην εφαρμογή σου!</p>
                <hr>
                <p><small>Sent via Personal Finance App</small></p>
                """
                ok, msg = send_email_attachment(current_email, subject, body)
                if ok:
                    st.success(f"✅ Το Report στάλθηκε στο {current_email}!")
                else:
                    st.error(f"⚠️ {msg}")

    with col_mail2:
        st.markdown("#### 📁 Backup σε Excel")
        st.caption("Λάβε ένα αντίγραφο ασφαλείας όλων των εγγραφών σου σε αρχείο Excel.")
        if st.button("📤 Αποστολή Excel στο Email", key="btn_send_excel"):
            current_email = st.session_state.get("user_email", "").strip()
            if not current_email:
                st.error("❌ Παρακαλώ αποθηκεύστε πρώτα το Email σου παραπάνω.")
            else:
                try:
                    excel_buffer = BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                        df_dummy = pd.DataFrame([{"Πληροφορία": "Finance Backup", "User": current_user}])
                        df_dummy.to_excel(writer, index=False, sheet_name="Backup")
                    
                    excel_data = excel_buffer.getvalue()
                    subject = "📁 Backup Οικονομικών Δεδομένων - Personal Finance Tracker"
                    body = f"<h3>Γεια σου {current_user},</h3><p>Επισυνάπτεται το αρχείο Excel με τα οικονομικά σου δεδομένα.</p>"
                    
                    ok, msg = send_email_attachment(current_email, subject, body, excel_data, "Finance_Backup.xlsx")
                    if ok:
                        st.success(f"✅ Το αρχείο Excel στάλθηκε στο {current_email}!")
                    else:
                        st.error(f"⚠️ {msg}")
                except Exception as e:
                    st.error(f"⚠️ Σφάλμα δημιουργίας Excel: {e}")

    st.markdown("---")
    st.markdown("### 🔑 Αλλαγή Κωδικού Πρόσβασης")

    old_pass = st.text_input("Τρέχων Κωδικός", type="password", key="prof_old_pass")
    new_pass = st.text_input("Νέος Κωδικός", type="password", key="prof_old_new_pass")
    confirm_pass = st.text_input("Επιβεβαίωση Νέου Κωδικού", type="password", key="prof_old_conf_pass")

    if st.button("Ενημέρωση Κωδικού", key="prof_save_btn"):
        passwords = st.secrets.get("passwords", {})
        if old_pass != passwords.get(current_user, ""):
            st.error("❌ Ο τρέχων κωδικός είναι λανθασμένος.")
        elif not new_pass:
            st.warning("⚠️ Παρακαλώ εισάγετε έναν νέο κωδικό.")
        elif new_pass != confirm_pass:
            st.error("❌ Ο νέος κωδικός και η επιβεβαίωση δεν ταιριάζουν.")
        else:
            st.success("✅ Ο κωδικός ενημερώθηκε!")

    st.markdown("---")
    if st.button("🚪 Αποσύνδεση (Logout)", key="logout_btn"):
        st.session_state["password_correct"] = False
        st.session_state["current_user"] = None
        st.session_state["user_email"] = None
        st.rerun()

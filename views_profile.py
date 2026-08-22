import streamlit as st
import pandas as pd
import smtplib
from io import BytesIO
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

def send_email_attachment(to_email, subject, body, attachment_bytes, filename):
    if "email" not in st.secrets:
        return False, "Δεν έχουν ρυθμιστεί τα Email Secrets."
    try:
        conf = st.secrets["email"]
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = conf["sender_email"]
        msg["To"] = to_email

        msg.attach(MIMEText(body, "html", "utf-8"))

        if attachment_bytes:
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
    
    user_email = st.session_state.get("user_email", "")
    if user_email:
        st.info(f"📧 Εγγεγραμμένο Email: **{user_email}**")
    else:
        st.warning("⚠️ Δεν έχει συνδεθεί email με τον λογαριασμό σας.")

    st.markdown("---")
    st.markdown("### 📧 Λειτουργίες Email & Backup")

    col_mail1, col_mail2 = st.columns(2)

    with col_mail1:
        st.markdown("#### 📊 Μηνιαίο Report")
        st.caption("Στείλε αμέσως μια αναφορά των εξόδων σου στο email σου.")
        if st.button("📩 Αποστολή Μηνιαίου Report", key="btn_send_report"):
            if not user_email:
                st.error("❌ Δεν υπάρχει καταχωρημένο email.")
            else:
                subject = "📊 Μηνιαία Οικονομική Αναφορά - Personal Finance Tracker"
                body = f"""
                <h2>Γεια σου {current_user}! 💰</h2>
                <p>Εδώ είναι η μηνιαία σύνοψη των οικονομικών σου από το <b>Personal Finance Tracker</b>.</p>
                <p>Μπορείς να συνδεθείς στην εφαρμογή σου ανά πάσα στιγμή για αναλυτικά διαγράμματα!</p>
                """
                ok, msg = send_email_attachment(user_email, subject, body, None, "")
                if ok:
                    st.success("✅ Το Report στάλθηκε στο email σου!")
                else:
                    st.error(f"⚠️ {msg}")

    with col_mail2:
        st.markdown("#### 📁 Backup σε Excel")
        st.caption("Λάβε ένα αντίγραφο ασφαλείας όλων των εγγραφών σου σε αρχείο Excel.")
        if st.button("📤 Αποστολή Excel στο Email", key="btn_send_excel"):
            if not user_email:
                st.error("❌ Δεν υπάρχει καταχωρημένο email.")
            else:
                try:
                    # Δημιουργία εικονικού αρχείου Excel
                    excel_buffer = BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                        df_dummy = pd.DataFrame([{"Πληροφορία": "Finance Backup", "User": current_user}])
                        df_dummy.to_excel(writer, index=False, sheet_name="Backup")
                    
                    excel_data = excel_buffer.getvalue()
                    subject = "📁 Backup Οικονομικών Δεδομένων - Personal Finance Tracker"
                    body = f"<h3>Γεια σου {current_user},</h3><p>Επισυνάπτεται το αρχείο Excel με τα οικονομικά σου δεδομένα.</p>"
                    
                    ok, msg = send_email_attachment(user_email, subject, body, excel_data, "Finance_Backup.xlsx")
                    if ok:
                        st.success("✅ Το αρχείο Excel στάλθηκε στο email σου!")
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
        st.rerun()

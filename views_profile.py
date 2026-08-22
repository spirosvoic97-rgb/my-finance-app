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

def render_profile(users_sheet, worksheet, current_user, t=None):
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

    # --- ΔΙΑΒΑΣΜΑ ΔΕΔΟΜΕΝΩΝ ΓΙΑ REPORT & BACKUP ---
    user_df = pd.DataFrame()
    try:
        all_vals = worksheet.get_all_values()
        if len(all_vals) > 1:
            clean_headers = [str(h).strip() for h in all_vals[0]]
            df_all = pd.DataFrame(all_vals[1:], columns=clean_headers)
            if "Username" in df_all.columns:
                user_df = df_all[df_all["Username"] == current_user].copy()
            else:
                user_df = df_all.copy()
    except Exception:
        pass

    with col_mail1:
        st.markdown("#### 📊 Μηνιαίο Report")
        st.caption("Στείλε μια αναλυτική αναφορά των εξόδων σου στο email σου.")
        if st.button("📩 Αποστολή Μηνιαίου Report", key="btn_send_report"):
            current_email = st.session_state.get("user_email", "").strip()
            if not current_email:
                st.error("❌ Παρακαλώ αποθηκεύστε πρώτα το Email σου παραπάνω.")
            else:
                # Υπολογισμός στατιστικών
                total_income, total_expense = 0.0, 0.0
                recent_rows_html = ""
                
                if not user_df.empty and "Ποσό" in user_df.columns and "Τύπος" in user_df.columns:
                    num_amt = pd.to_numeric(user_df["Ποσό"].astype(str).str.replace(",", "."), errors="coerce").fillna(0.0)
                    total_income = num_amt[user_df["Τύπος"] == "Έσοδο"].sum()
                    total_expense = num_amt[user_df["Τύπος"] == "Έξοδο"].sum()
                    
                    # Πίνακας πρόσφατων εγγραφών
                    recent_df = user_df.tail(8)
                    recent_rows_html = "".join([
                        f"<tr><td style='padding:6px;border:1px solid #ddd;'>{row.get('Ημερομηνία','')}</td>"
                        f"<td style='padding:6px;border:1px solid #ddd;'>{row.get('Περιγραφή','')}</td>"
                        f"<td style='padding:6px;border:1px solid #ddd;'>{row.get('Κατηγορία','')}</td>"
                        f"<td style='padding:6px;border:1px solid #ddd;font-weight:bold;'>{row.get('Ποσό','')} €</td></tr>"
                        for _, row in recent_df.iterrows()
                    ])

                balance = total_income - total_expense

                subject = f"📊 Μηνιαία Οικονομική Αναφορά - {current_user}"
                body = f"""
                <div style="font-family: Arial, sans-serif; color: #333; max-width: 600px;">
                    <h2 style="color: #2e7d32;">💰 Μηνιαίο Report - Personal Finance Tracker</h2>
                    <p>Γεια σου <b>{current_user}</b>! Εδώ είναι η σύνοψη των οικονομικών σου:</p>
                    
                    <div style="background-color: #f5f5f5; padding: 15px; border-radius: 8px; margin: 15px 0;">
                        <p style="margin: 5px 0;"><b>💵 Συνολικά Έσοδα:</b> <span style="color:#2e7d32;">{total_income:.2f} €</span></p>
                        <p style="margin: 5px 0;"><b>💸 Συνολικά Έξοδα:</b> <span style="color:#c62828;">{total_expense:.2f} €</span></p>
                        <hr style="border:0; border-top:1px solid #ccc;">
                        <p style="margin: 5px 0; font-size:1.1em;"><b>💳 Διαθέσιμο Υπόλοιπο:</b> <b>{balance:.2f} €</b></p>
                    </div>

                    <h3>📋 Πρόσφατες Εγγραφές:</h3>
                    <table style="width:100%; border-collapse:collapse; font-size:14px;">
                        <thead>
                            <tr style="background-color:#0288d1; color:white;">
                                <th style="padding:8px;border:1px solid #ddd;">Ημερομηνία</th>
                                <th style="padding:8px;border:1px solid #ddd;">Περιγραφή</th>
                                <th style="padding:8px;border:1px solid #ddd;">Κατηγορία</th>
                                <th style="padding:8px;border:1px solid #ddd;">Ποσό</th>
                            </tr>
                        </thead>
                        <tbody>
                            {recent_rows_html if recent_rows_html else "<tr><td colspan='4' style='padding:8px;'>Δεν υπάρχουν εγγραφές.</td></tr>"}
                        </tbody>
                    </table>

                    <br>
                    <p><small>Sent automatically via Personal Finance App</small></p>
                </div>
                """
                ok, msg = send_email_attachment(current_email, subject, body)
                if ok:
                    st.success(f"✅ Το αναλυτικό Report στάλθηκε στο {current_email}!")
                else:
                    st.error(f"⚠️ {msg}")

    with col_mail2:
        st.markdown("#### 📁 Backup σε Excel")
        st.caption("Λάβε ένα πλήρες αντίγραφο ασφαλείας όλων των εγγραφών σου σε αρχείο Excel.")
        if st.button("📤 Αποστολή Excel στο Email", key="btn_send_excel"):
            current_email = st.session_state.get("user_email", "").strip()
            if not current_email:
                st.error("❌ Παρακαλώ αποθηκεύστε πρώτα το Email σου παραπάνω.")
            else:
                try:
                    excel_buffer = BytesIO()
                    
                    # Καθαρισμός στηλών για το Excel
                    export_df = user_df.copy() if not user_df.empty else pd.DataFrame([{"Πληροφορία": "Δεν βρέθηκαν εγγραφές"}])
                    
                    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                        export_df.to_excel(writer, index=False, sheet_name="Finance_Data")
                    
                    excel_data = excel_buffer.getvalue()
                    subject = f"📁 Backup Οικονομικών Δεδομένων - {current_user}"
                    body = f"""
                    <h3>Γεια σου {current_user},</h3>
                    <p>Επισυνάπτεται το πλήρες αρχείο Excel (<code>Finance_Backup.xlsx</code>) με όλες τις καταχωρήσεις σου.</p>
                    <p><small>Sent via Personal Finance App</small></p>
                    """
                    
                    ok, msg = send_email_attachment(current_email, subject, body, excel_data, f"Finance_Backup_{current_user}.xlsx")
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

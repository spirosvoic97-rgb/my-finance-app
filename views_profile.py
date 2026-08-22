import streamlit as st

def render_profile(users_sheet, current_user):
    st.subheader("⚙️ Διαχείριση Προφίλ & Ρυθμίσεις")
    st.write(f"Συνδεδεμένος χρήστης: **{current_user}**")

    st.markdown("---")
    st.markdown("#### 🔑 Αλλαγή Κωδικού Πρόσβασης")

    old_pass = st.text_input("Τρέχων Κωδικός", type="password", key="prof_old_pass")
    new_pass = st.text_input("Νέος Κωδικός", type="password", key="prof_new_pass")
    confirm_pass = st.text_input("Επιβεβαίωση Νέου Κωδικού", type="password", key="prof_conf_pass")

    if st.button("Ενημέρωση Κωδικού", key="prof_save_btn"):
        passwords = st.secrets.get("passwords", {})
        
        if old_pass != passwords.get(current_user, ""):
            st.error("❌ Ο τρέχων κωδικός είναι λανθασμένος.")
        elif not new_pass:
            st.warning("⚠️ Παρακαλώ εισάγετε έναν νέο κωδικό.")
        elif new_pass != confirm_pass:
            st.error("❌ Ο νέος κωδικός και η επιβεβαίωση δεν ταιριάζουν.")
        else:
            st.success("✅ Ο κωδικός ενημερώθηκε! (Σημείωση: Για μόνιμη αλλαγή, ενημερώστε τα Secrets στο Streamlit Cloud).")

    st.markdown("---")
    if st.button("🚪 Αποσύνδεση (Logout)", key="logout_btn"):
        st.session_state["password_correct"] = False
        st.session_state["current_user"] = None
        st.rerun()

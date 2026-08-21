import streamlit as st
import json
import pandas as pd
from auth import check_hash, make_hash

def render_profile(users_sheet, current_user, user_email, STARTING_BALANCE, df, worksheet, theme):
    st.subheader("🎨 Εμφάνιση")
    new_theme = st.radio("Θέμα Εμφάνισης", ["Dark Mode 🌙", "Light Mode ☀️"], index=0 if theme == "Dark Mode 🌙" else 1, horizontal=True)
    if new_theme != theme:
        st.session_state["theme"] = new_theme
        st.rerun()

    st.markdown("---")
    st.subheader("💰 Αρχικό Ταμείο")
    new_start_bal = st.number_input("Ορισμός Αρχικού Υπολοίπου (€)", value=float(STARTING_BALANCE), step=50.00, key="set_start_bal")
    if st.button("Ενημέρωση Αρχικού Ταμείου"):
        try:
            users_data = users_sheet.get_all_records()
            user_row_idx = None
            for idx, u in enumerate(users_data):
                if str(u.get("Username", "")).strip().lower() == current_user.lower():
                    user_row_idx = idx + 2
                    break
            if user_row_idx:
                users_sheet.update_cell(user_row_idx, 5, new_start_bal)
                st.session_state["starting_balance"] = new_start_bal
                st.success("✅ Το Αρχικό Ταμείο ενημερώθηκε επιτυχώς!")
                st.rerun()
        except Exception:
            st.error("❌ Σφάλμα κατά την ενημέρωση.")

    st.markdown("---")
    st.subheader("💾 Backup / Restore Δεδομένων (JSON)")
    col_j1, col_p2 = st.columns(2)
    with col_j1:
        if not df.empty:
            json_str = df.to_json(orient="records", force_ascii=False)
            st.download_button(label="📥 Download JSON Backup", data=json_str, file_name=f"finance_backup_{current_user}.json", mime="application/json")
    with col_p2:
        uploaded_json = st.file_uploader("Εισαγωγή JSON Backup", type=["json"], key="json_restore")
        if uploaded_json is not None:
            if st.button("🔄 Επαναφορά Δεδομένων"):
                try:
                    restore_data = json.load(uploaded_json)
                    for item in restore_data:
                        worksheet.append_row([
                            str(item.get("Ημερομηνία")), str(item.get("Περιγραφή", "")),
                            str(item.get("Τύπος")), str(item.get("Κατηγορία")),
                            float(item.get("Ποσό", 0.0)), str(item.get("Επαναλαμβανόμενο", "Όχι")), current_user
                        ], value_input_option="USER_ENTERED")
                    st.cache_data.clear()
                    st.success("🎉 Τα δεδομένα επαναφέρθηκαν επιτυχώς!")
                    st.rerun()
                except Exception:
                    st.error("❌ Σφάλμα κατά την ανάγνωση του αρχείου JSON.")

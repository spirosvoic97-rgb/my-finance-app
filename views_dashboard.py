import streamlit as st
import pandas as pd

def render_dashboard(worksheet, current_user):
    st.subheader("📊 Αναφορές & Analytics")

    try:
        data = worksheet.get_all_values()
    except Exception as e:
        st.error(f"⚠️ Σφάλμα κατά τη ανάγνωση του Google Sheet: {e}")
        return

    if not data or len(data) <= 1:
        st.info("Δεν υπάρχουν ακόμα εγγραφές στο Google Sheet.")
        return

    # Δημιουργία DataFrame
    headers = data[0]
    rows = data[1:]
    df = pd.DataFrame(rows, columns=headers)

    # Φιλτράρισμα ανά χρήστη αν υπάρχει η στήλη Username
    if "Username" in df.columns:
        df = df[df["Username"] == current_user]

    if df.empty:
        st.info(f"Δεν βρέθηκαν εγγραφές για τον χρήστη {current_user}.")
        return

    # Υπολογισμός ποσών σε ξεχωριστή αριθμητική στήλη
    if "Ποσό" in df.columns:
        numeric_amounts = pd.to_numeric(df["Ποσό"].astype(str).str.replace(",", "."), errors="coerce").fillna(0.0)
    else:
        st.warning("Δεν βρέθηκε στήλη 'Ποσό' στο φύλλο εργασίας.")
        return

    # Υπολογισμός Συνόλων
    total_income = numeric_amounts[df["Τύπος"] == "Έσοδο"].sum() if "Τύπος" in df.columns else 0.0
    total_expense = numeric_amounts[df["Τύπος"] == "Έξοδο"].sum() if "Τύπος" in df.columns else 0.0
    balance = total_income - total_expense

    # Εμφάνιση Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Συνολικά Έσοδα", f"{total_income:.2f} €")
    col2.metric("💸 Συνολικά Έξοδα", f"{total_expense:.2f} €")
    col3.metric("⚖️ Υπόλοιπο", f"{balance:.2f} €")

    st.markdown("---")

    # Ανάλυση Εξόδων ανά Κατηγορία & Διάγραμμα
    if "Τύπος" in df.columns and "Κατηγορία" in df.columns:
        df_expenses_mask = df["Τύπος"] == "Έξοδο"
        if df_expenses_mask.any():
            st.subheader("📉 Έξοδα ανά Κατηγορία")
            df_chart = pd.DataFrame({
                "Κατηγορία": df.loc[df_expenses_mask, "Κατηγορία"],
                "Ποσό": numeric_amounts[df_expenses_mask]
            })
            cat_summary = df_chart.groupby("Κατηγορία")["Ποσό"].sum().reset_index()
            st.bar_chart(data=cat_summary, x="Κατηγορία", y="Ποσό")

    # Πίνακας Τελευταίων Εγγραφών (Μετατροπή σε string για αποφυγή PyArrow ValueErrors)
    st.markdown("---")
    st.subheader("📋 Τελευταίες Εγγραφές")
    df_display = df.astype(str).tail(10)
    st.dataframe(df_display, use_container_width=True)

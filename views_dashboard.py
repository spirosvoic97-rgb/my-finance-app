import streamlit as st
import pandas as pd

def render_dashboard(worksheet, current_user):
    st.subheader("📊 Αναφορές & Analytics")

    records = worksheet.get_all_records()
    df = pd.DataFrame(records)

    if df.empty:
        st.info("Δεν υπάρχουν ακόμα εγγραφές.")
        return

    # Φιλτράρισμα ανά χρήστη
    if "Username" in df.columns:
        df = df[df["Username"] == current_user]

    if df.empty:
        st.info(f"Δεν βρέθηκαν εγγραφές για τον χρήστη {current_user}.")
        return

    # Μετατροπή Ποσού σε αριθμό
    df["Ποσό"] = pd.to_numeric(df["Ποσό"], errors="coerce").fillna(0)

    # Υπολογισμός Συνόλων
    total_income = df[df["Τύπος"] == "Έσοδο"]["Ποσό"].sum()
    total_expense = df[df["Τύπος"] == "Έξοδο"]["Ποσό"].sum()
    balance = total_income - total_expense

    # Εμφάνιση Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Συνολικά Έσοδα", f"{total_income:.2f} €")
    col2.metric("💸 Συνολικά Έξοδα", f"{total_expense:.2f} €")
    col3.metric("⚖️ Υπόλοιπο", f"{balance:.2f} €")

    st.markdown("---")

    # Ανάλυση Εξόδων ανά Κατηγορία
    df_expenses = df[df["Τύπος"] == "Έξοδο"]
    if not df_expenses.empty:
        st.subheader("📉 Έξοδα ανά Κατηγορία")
        cat_summary = df_expenses.groupby("Κατηγορία")["Ποσό"].sum().reset_index()
        st.dataframe(cat_summary, use_container_width=True)
        st.bar_chart(data=cat_summary, x="Κατηγορία", y="Ποσό")

    # Πίνακας Τελευταίων Εγγραφών
    st.markdown("---")
    st.subheader("📋 Τελευταίες Εγγραφές")
    st.dataframe(df.tail(10), use_container_width=True)

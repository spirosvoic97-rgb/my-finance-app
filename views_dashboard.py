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

    # Καθαρισμός επικεφαλίδων
    raw_headers = data[0]
    clean_headers = [str(h).strip() if str(h).strip() else f"Col_{i+1}" for i, h in enumerate(raw_headers)]

    rows = data[1:]
    df = pd.DataFrame(rows, columns=clean_headers)

    # Φιλτράρισμα ανά χρήστη
    if "Username" in df.columns:
        df = df[df["Username"] == current_user]

    if df.empty:
        st.info(f"Δεν βρέθηκαν εγγραφές για τον χρήστη {current_user}.")
        return

    # Μετατροπή Ποσού σε αριθμό
    if "Ποσό" in df.columns:
        numeric_amounts = pd.to_numeric(df["Ποσό"].astype(str).str.replace(",", "."), errors="coerce").fillna(0.0)
    else:
        st.warning("Δεν βρέθηκε στήλη 'Ποσό' στο φύλλο εργασίας.")
        return

    # Υπολογισμός Συνόλων
    type_col = "Τύπος" if "Τύπος" in df.columns else None
    total_income = numeric_amounts[df[type_col] == "Έσοδο"].sum() if type_col else 0.0
    total_expense = numeric_amounts[df[type_col] == "Έξοδο"].sum() if type_col else 0.0
    balance = total_income - total_expense

    # Εμφάνιση Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Συνολικά Έσοδα", f"{total_income:.2f} €")
    col2.metric("💸 Συνολικά Έξοδα", f"{total_expense:.2f} €")
    col3.metric("⚖️ Υπόλοιπο", f"{balance:.2f} €")

    st.markdown("---")

    # Ανάλυση Εξόδων ανά Κατηγορία & Διάγραμμα
    cat_col = "Κατηγορία" if "Κατηγορία" in df.columns else None
    if type_col and cat_col:
        df_expenses_mask = df[type_col] == "Έξοδο"
        if df_expenses_mask.any():
            st.subheader("📉 Έξοδα ανά Κατηγορία")
            df_chart = pd.DataFrame({
                "Κατηγορία": df.loc[df_expenses_mask, cat_col],
                "Ποσό": numeric_amounts[df_expenses_mask]
            })
            cat_summary = df_chart.groupby("Κατηγορία")["Ποσό"].sum().reset_index()
            st.bar_chart(data=cat_summary, x="Κατηγορία", y="Ποσό")

    # Πίνακας Τελευταίων Εγγραφών (ΜΟΝΟ οι πρώτες 5 βασικές στήλες)
    st.markdown("---")
    st.subheader("📋 Τελευταίες Εγγραφές")
    
    desired_cols = ["Ημερομηνία", "Περιγραφή", "Τύπος", "Κατηγορία", "Ποσό"]
    available_cols = [c for c in desired_cols if c in df.columns]
    
    df_display = df[available_cols].tail(10).astype(str)
    st.table(df_display)

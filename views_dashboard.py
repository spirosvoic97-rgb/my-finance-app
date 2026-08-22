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

    # Μετατροπή Ημερομηνίας σε datetime αντικείμενα για φιλτράρισμα
    if "Ημερομηνία" in df.columns:
        df["Date_Parsed"] = pd.to_datetime(df["Ημερομηνία"], errors="coerce")
        df["Έτος"] = df["Date_Parsed"].dt.year.fillna(0).astype(int).astype(str)
        df["Μήνας_Num"] = df["Date_Parsed"].dt.month.fillna(0).astype(int)
        
        # Αντιστοίχιση μηνών σε ελληνικά ονόματα
        month_names = {
            0: "Άγνωστος", 1: "Ιανουάριος", 2: "Φεβρουάριος", 3: "Μάρτιος",
            4: "Απρίλιος", 5: "Μάιος", 6: "Ιούνιος", 7: "Ιούλιος",
            8: "Αύγουστος", 9: "Σεπτέμβριος", 10: "Οκτώβριος", 11: "Νοέμβριος", 12: "Δεκέμβριος"
        }
        df["Μήνας"] = df["Μήνας_Num"].map(month_names)
    else:
        st.warning("Δεν βρέθηκε στήλη 'Ημερομηνία'.")
        return

    # --- ΦΙΛΤΡΑ ΕΤΟΥΣ & ΜΗΝΑ ---
    st.markdown("#### 📅 Φίλτρα Χρονικής Περιόδου")
    col_filter1, col_filter2 = st.columns(2)

    available_years = sorted([y for y in df["Έτος"].unique() if y != "0"], reverse=True)
    year_options = ["Όλα"] + available_years
    
    with col_filter1:
        selected_year = st.selectbox("Επιλογή Έτους", year_options, key="filter_year")

    # Εφαρμογή φίλτρου έτους
    filtered_df = df.copy()
    if selected_year != "Όλα":
        filtered_df = filtered_df[filtered_df["Έτος"] == selected_year]

    # Διαθέσιμοι μήνες με βάση το επιλεγμένο έτος
    available_months_num = sorted([m for m in filtered_df["Μήνας_Num"].unique() if m != 0])
    month_options = ["Όλοι"] + [month_names[m] for m in available_months_num]

    with col_filter2:
        selected_month = st.selectbox("Επιλογή Μήνα", month_options, key="filter_month")

    # Εφαρμογή φίλτρου μήνα
    if selected_month != "Όλοι":
        filtered_df = filtered_df[filtered_df["Μήνας"] == selected_month]

    st.markdown("---")

    if filtered_df.empty:
        st.warning("Δεν βρέθηκαν εγγραφές για τη συγκεκριμένη περίοδο.")
        return

    # Μετατροπή Ποσού σε αριθμό
    if "Ποσό" in filtered_df.columns:
        numeric_amounts = pd.to_numeric(filtered_df["Ποσό"].astype(str).str.replace(",", "."), errors="coerce").fillna(0.0)
    else:
        st.warning("Δεν βρέθηκε στήλη 'Ποσό' στο φύλλο εργασίας.")
        return

    # Υπολογισμός Συνόλων
    type_col = "Τύπος" if "Τύπος" in filtered_df.columns else None
    total_income = numeric_amounts[filtered_df[type_col] == "Έσοδο"].sum() if type_col else 0.0
    total_expense = numeric_amounts[filtered_df[type_col] == "Έξοδο"].sum() if type_col else 0.0
    balance = total_income - total_expense

    # Εμφάνιση Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Συνολικά Έσοδα", f"{total_income:.2f} €")
    col2.metric("💸 Συνολικά Έξοδα", f"{total_expense:.2f} €")
    col3.metric("⚖️ Υπόλοιπο", f"{balance:.2f} €")

    st.markdown("---")

    # Ανάλυση Εξόδων ανά Κατηγορία & Διάγραμμα
    cat_col = "Κατηγορία" if "Κατηγορία" in filtered_df.columns else None
    if type_col and cat_col:
        df_expenses_mask = filtered_df[type_col] == "Έξοδο"
        if df_expenses_mask.any():
            st.subheader("📉 Έξοδα ανά Κατηγορία")
            df_chart = pd.DataFrame({
                "Κατηγορία": filtered_df.loc[df_expenses_mask, cat_col],
                "Ποσό": numeric_amounts[df_expenses_mask]
            })
            cat_summary = df_chart.groupby("Κατηγορία")["Ποσό"].sum().reset_index()
            st.bar_chart(data=cat_summary, x="Κατηγορία", y="Ποσό")

    # Πίνακας Εγγραφών (ΜΟΝΟ οι 5 βασικές στήλες)
    st.markdown("---")
    st.subheader("📋 Εγγραφές Περιόδου")
    
    desired_cols = ["Ημερομηνία", "Περιγραφή", "Τύπος", "Κατηγορία", "Ποσό"]
    available_cols = [c for c in desired_cols if c in filtered_df.columns]
    
    df_display = filtered_df[available_cols].tail(15).astype(str)
    st.table(df_display)

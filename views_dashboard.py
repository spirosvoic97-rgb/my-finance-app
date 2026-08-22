import streamlit as st
import pandas as pd
import plotly.express as px

def render_dashboard(worksheet, current_user, t=None):
    if t is None: t = {}

    st.subheader(t.get("dash_title", "📊 Αναφορές & Analytics"))

    try:
        data = worksheet.get_all_values()
    except Exception as e:
        st.error(f"⚠️ Σφάλμα κατά τη ανάγνωση του Google Sheet: {e}")
        return

    if not data or len(data) <= 1:
        st.info("Δεν υπάρχουν ακόμα εγγραφές στο Google Sheet.")
        return

    raw_headers = data[0]
    clean_headers = [str(h).strip() if str(h).strip() else f"Col_{i+1}" for i, h in enumerate(raw_headers)]

    rows = data[1:]
    df = pd.DataFrame(rows, columns=clean_headers)

    if "Username" in df.columns:
        df = df[df["Username"] == current_user]

    if df.empty:
        st.info(f"Δεν βρέθηκαν εγγραφές για τον χρήστη {current_user}.")
        return

    if "Ημερομηνία" in df.columns:
        df["Date_Parsed"] = pd.to_datetime(df["Ημερομηνία"], errors="coerce")
        df["Έτος"] = df["Date_Parsed"].dt.year.fillna(0).astype(int).astype(str)
        df["Μήνας_Num"] = df["Date_Parsed"].dt.month.fillna(0).astype(int)

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
    st.markdown(f"#### {t.get('dash_filters', '📅 Φίλτρα Χρονικής Περιόδου')}")
    col_filter1, col_filter2 = st.columns(2)

    available_years = sorted([y for y in df["Έτος"].unique() if y != "0"], reverse=True)
    year_options = [t.get("all", "Όλα")] + available_years

    with col_filter1:
        selected_year = st.selectbox(t.get("dash_year", "Επιλογή Έτους"), year_options, key="filter_year")

    filtered_df = df.copy()
    if selected_year != t.get("all", "Όλα"):
        filtered_df = filtered_df[filtered_df["Έτος"] == selected_year]

    available_months_num = sorted([m for m in filtered_df["Μήνας_Num"].unique() if m != 0])
    month_options = [t.get("all", "Όλοι")] + [month_names[m] for m in available_months_num]

    with col_filter2:
        selected_month = st.selectbox(t.get("dash_month", "Επιλογή Μήνα"), month_options, key="filter_month")

    if selected_month != t.get("all", "Όλοι"):
        filtered_df = filtered_df[filtered_df["Μήνας"] == selected_month]

    st.markdown("---")

    if filtered_df.empty:
        st.warning("Δεν βρέθηκαν εγγραφές για τη συγκεκριμένη περίοδο.")
        return

    if "Ποσό" in filtered_df.columns:
        numeric_amounts = pd.to_numeric(filtered_df["Ποσό"].astype(str).str.replace(",", "."), errors="coerce").fillna(0.0)
    else:
        st.warning("Δεν βρέθηκε στήλη 'Ποσό' στο φύλλο εργασίας.")
        return

    type_col = "Τύπος" if "Τύπος" in filtered_df.columns else None
    cat_col = "Κατηγορία" if "Κατηγορία" in filtered_df.columns else None

    # --- ΕΛΕΓΧΟΣ SAFE TO SPEND (ΒΕΛΤΙΩΜΕΝΟΣ) ---
    total_income = numeric_amounts[filtered_df[type_col] == "Έσοδο"].sum() if type_col else 0.0
    total_expense = numeric_amounts[filtered_df[type_col] == "Έξοδο"].sum() if type_col else 0.0
    period_balance = total_income - total_expense

    fixed_expenses = 0.0
    if cat_col and type_col:
        # Έλεγχος αν η κατηγορία περιέχει τις λέξεις Πάγια, Λογαριασμοί ή Αποταμίευση (Case-Insensitive)
        cat_series = filtered_df[cat_col].astype(str).str.lower()
        fixed_mask = (filtered_df[type_col] == "Έξοδο") & (
            cat_series.str.contains("πάγια", na=False) | 
            cat_series.str.contains("λογαριασμ", na=False) | 
            cat_series.str.contains("αποταμίευση", na=False)
        )
        fixed_expenses = numeric_amounts[fixed_mask].sum()

    safe_to_spend = max(0.0, period_balance - fixed_expenses) if period_balance > 0 else 0.0

    col1, col2, col3 = st.columns(3)
    col1.metric(t.get("dash_inc", "💰 Έσοδα Περιόδου"), f"{total_income:.2f} €")
    col2.metric(t.get("dash_exp", "💸 Έξοδα Περιόδου"), f"{total_expense:.2f} €")
    col3.metric("🟢 Safe to Spend", f"{safe_to_spend:.2f} €", help="Διαθέσιμο ποσό αφού υπολογιστούν τα Πάγια και η Αποταμίευση")

    st.markdown("---")

    # --- COMPACT ΤΑΞΙΝΟΜΗΣΗ & ΠΙΝΑΚΑΣ ΕΓΓΡΑΦΩΝ (ΕΠΑΝΩ) ---
    col_table_title, col_sort_compact = st.columns([3, 2])
    with col_table_title:
        st.subheader("📋 Εγγραφές Περιόδου")
    with col_sort_compact:
        sort_order = st.selectbox(
            "⇅ Ταξινόμηση κατά",
            ["Ημερομηνία (Νεότερες)", "Ημερομηνία (Παλαιότερες)", "Ποσό (Μεγαλύτερα)", "Ποσό (Μικρότερα)"],
            key="compact_sort_select",
            label_visibility="collapsed"
        )

    filtered_df["Clean_Amount"] = numeric_amounts
    filtered_df["Ποσό (€)"] = numeric_amounts

    # Εφαρμογή Ταξινόμησης
    if sort_order == "Ημερομηνία (Νεότερες)":
        filtered_df = filtered_df.sort_values(by="Date_Parsed", ascending=False)
    elif sort_order == "Ημερομηνία (Παλαιότερες)":
        filtered_df = filtered_df.sort_values(by="Date_Parsed", ascending=True)
    elif sort_order == "Ποσό (Μεγαλύτερα)":
        filtered_df = filtered_df.sort_values(by="Clean_Amount", ascending=False)
    elif sort_order == "Ποσό (Μικρότερα)":
        filtered_df = filtered_df.sort_values(by="Clean_Amount", ascending=True)

    desired_cols = ["Ημερομηνία", "Περιγραφή", "Τύπος", "Κατηγορία", "Ποσό"]
    available_cols = [c for c in desired_cols if c in filtered_df.columns]

    st.table(filtered_df[available_cols].astype(str))

    st.markdown("---")

    # --- DROP-DOWN SELECTOR ΓΙΑ ΕΠΙΛΟΓΗ ΔΙΑΓΡΑΜΜΑΤΟΣ (ΚΑΤΩ) ---
    st.subheader("📊 Επιλογή Διαγράμματος")
    chart_choice = st.selectbox(
        "Διάλεξε γράφημα για προβολή:",
        [
            "📉 Κατανομή Εξόδων (Πίτα)",
            "📈 Κατανομή Εσόδων (Πίτα)",
            "📊 Έξοδα ανά Κατηγορία (Ράβδοι)",
            "📊 Σωρευτικό Διάγραμμα Εξόδων (Stacked)",
            "⚖️ Σύγκριση Εσόδων vs Εξόδων"
        ],
        key="chart_selector"
    )

    if chart_choice == "📉 Κατανομή Εξόδων (Πίτα)":
        df_exp = filtered_df[filtered_df[type_col] == "Έξοδο"]
        if not df_exp.empty:
            cat_sum = df_exp.groupby(cat_col)["Ποσό (€)"].sum().reset_index()
            fig = px.pie(cat_sum, values="Ποσό (€)", names=cat_col, hole=0.4, title="Κατανομή Εξόδων ανά Κατηγορία")
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(dragmode=False)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("Δεν υπάρχουν έξοδα για προβολή.")

    elif chart_choice == "📈 Κατανομή Εσόδων (Πίτα)":
        df_inc = filtered_df[filtered_df[type_col] == "Έσοδο"]
        if not df_inc.empty:
            cat_sum = df_inc.groupby(cat_col)["Ποσό (€)"].sum().reset_index()
            fig = px.pie(cat_sum, values="Ποσό (€)", names=cat_col, hole=0.4, title="Κατανομή Εσόδων ανά Κατηγορία")
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(dragmode=False)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("Δεν υπάρχουν έσοδα για προβολή.")

    elif chart_choice == "📊 Έξοδα ανά Κατηγορία (Ράβδοι)":
        df_exp = filtered_df[filtered_df[type_col] == "Έξοδο"]
        if not df_exp.empty:
            cat_sum = df_exp.groupby(cat_col)["Ποσό (€)"].sum().reset_index()
            fig = px.bar(
                cat_sum, 
                x=cat_col, 
                y="Ποσό (€)", 
                color=cat_col, 
                title="Έξοδα ανά Κατηγορία", 
                text_auto='.2f',
                labels={"Ποσό (€)": "Ποσό (€)", cat_col: "Κατηγορία"}
            )
            fig.update_layout(dragmode=False, showlegend=False)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("Δεν υπάρχουν έξοδα για προβολή.")

    elif chart_choice == "📊 Σωρευτικό Διάγραμμα Εξόδων (Stacked)":
        df_exp = filtered_df[filtered_df[type_col] == "Έξοδο"]
        if not df_exp.empty:
            fig = px.bar(
                df_exp, 
                x="Μήνας", 
                y="Ποσό (€)", 
                color=cat_col, 
                title="Σωρευτική Ανάλυση Εξόδων ανά Μήνα", 
                barmode="stack",
                labels={"Ποσό (€)": "Ποσό (€)", "Μήνας": "Μήνας", cat_col: "Κατηγορία"}
            )
            fig.update_layout(dragmode=False)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("Δεν υπάρχουν έξοδα για προβολή.")

    elif chart_choice == "⚖️ Σύγκριση Εσόδων vs Εξόδων":
        type_sum = filtered_df.groupby([type_col, "Μήνας"])["Ποσό (€)"].sum().reset_index()
        fig = px.bar(
            type_sum, 
            x="Μήνας", 
            y="Ποσό (€)", 
            color=type_col, 
            barmode="group", 
            title="Σύγκριση Εσόδων & Εξόδων ανά Μήνα", 
            text_auto='.2f',
            labels={"Ποσό (€)": "Ποσό (€)", "Μήνας": "Μήνας", type_col: "Τύπος"}
        )
        fig.update_layout(dragmode=False)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

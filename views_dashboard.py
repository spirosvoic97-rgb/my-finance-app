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
        df["Date_Parsed"] = pd.to_datetime(df["Ημερομηνία"], format="%Y-%m-%d", errors="coerce")
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

    if "Ποσό" in df.columns:
        numeric_amounts = pd.to_numeric(df["Ποσό"].astype(str).str.replace(",", "."), errors="coerce").fillna(0.0)
    else:
        st.warning("Δεν βρέθηκε στήλη 'Ποσό' στο φύλλο εργασίας.")
        return

    type_col = "Τύπος" if "Τύπος" in df.columns else None
    cat_col = "Κατηγορία" if "Κατηγορία" in df.columns else None

    # --- HELPER LOGIC FOR SAFE TO SPEND ---
    def calculate_fixed_expenses(data_df, amounts_series):
        if not cat_col or not type_col or data_df.empty:
            return 0.0
        
        # Καθαρισμός κειμένου κατηγοριών (μικρά, χωρίς τόνους)
        clean_cats = (
            data_df[cat_col]
            .astype(str)
            .str.lower()
            .str.replace("ά", "α")
            .str.replace("έ", "ε")
            .str.replace("ή", "η")
            .str.replace("ί", "ι")
            .str.replace("ό", "ο")
            .str.replace("ύ", "υ")
            .str.replace("ώ", "ω")
        )
        
        # Αναζήτηση λέξεων κλειδιών για Πάγια & Αποταμίευση
        fixed_mask = (data_df[type_col] == "Έξοδο") & (
            clean_cats.str.contains("παγια", na=False) | 
            clean_cats.str.contains("λογαριασμ", na=False) | 
            clean_cats.str.contains("αποταμιευση", na=False) |
            clean_cats.str.contains("ενοικι", na=False)
        )
        return amounts_series[fixed_mask].sum()

    # --- 1. TOP METRICS ---
    total_income = numeric_amounts[df[type_col] == "Έσοδο"].sum() if type_col else 0.0
    total_expense = numeric_amounts[df[type_col] == "Έξοδο"].sum() if type_col else 0.0
    period_balance = total_income - total_expense

    fixed_exp_total = calculate_fixed_expenses(df, numeric_amounts)
    safe_to_spend_total = max(0.0, period_balance - fixed_exp_total) if period_balance > 0 else 0.0

    col1, col2, col3 = st.columns(3)
    metric_inc = col1.metric(t.get("dash_inc", "💰 Έσοδα Περιόδου"), f"{total_income:.2f} €")
    metric_exp = col2.metric(t.get("dash_exp", "💸 Έξοδα Περιόδου"), f"{total_expense:.2f} €")
    metric_safe = col3.metric("🟢 Safe to Spend", f"{safe_to_spend_total:.2f} €", help="Διαθέσιμο υπόλοιπο μείων τα Πάγια/Λογαριασμούς & Αποταμίευση")

    st.markdown("---")

    # --- 2. ΦΙΛΤΡΑ & ΠΙΝΑΚΑΣ ΕΓΓΡΑΦΩΝ ---
    st.subheader("📋 Εγγραφές & Φίλτρα Περιόδου")
    
    col_filter1, col_filter2, col_sort_compact = st.columns([2, 2, 3])

    available_years = sorted([y for y in df["Έτος"].unique() if y != "0"], reverse=True)
    year_options = [t.get("all", "Όλα")] + available_years
    with col_filter1:
        selected_year = st.selectbox(t.get("dash_year", "Έτος"), year_options, key="filter_year")

    filtered_df = df.copy()
    if selected_year != t.get("all", "Όλα"):
        filtered_df = filtered_df[filtered_df["Έτος"] == selected_year]

    available_months_num = sorted([m for m in filtered_df["Μήνας_Num"].unique() if m != 0])
    month_options = [t.get("all", "Όλοι")] + [month_names[m] for m in available_months_num]
    with col_filter2:
        selected_month = st.selectbox(t.get("dash_month", "Μήνας"), month_options, key="filter_month")

    if selected_month != t.get("all", "Όλοι"):
        filtered_df = filtered_df[filtered_df["Μήνας"] == selected_month]

    with col_sort_compact:
        sort_order = st.selectbox(
            "⇅ Ταξινόμηση κατά",
            ["Ημερομηνία (Νεότερες πρώτα)", "Ημερομηνία (Παλαιότερες πρώτα)", "Ποσό (Μεγαλύτερα)", "Ποσό (Μικρότερα)"],
            key="compact_sort_select"
        )

    # Ενημέρωση των Metrics με βάση τα ενεργά φίλτρα
    if not filtered_df.empty:
        filtered_amounts = pd.to_numeric(filtered_df["Ποσό"].astype(str).str.replace(",", "."), errors="coerce").fillna(0.0)
        total_income_f = filtered_amounts[filtered_df[type_col] == "Έσοδο"].sum() if type_col else 0.0
        total_expense_f = filtered_amounts[filtered_df[type_col] == "Έξοδο"].sum() if type_col else 0.0
        period_balance_f = total_income_f - total_expense_f
        
        fixed_exp_f = calculate_fixed_expenses(filtered_df, filtered_amounts)
        safe_to_spend_f = max(0.0, period_balance_f - fixed_exp_f) if period_balance_f > 0 else 0.0
        
        metric_inc.metric(t.get("dash_inc", "💰 Έσοδα Περιόδου"), f"{total_income_f:.2f} €")
        metric_exp.metric(t.get("dash_exp", "💸 Έξοδα Περιόδου"), f"{total_expense_f:.2f} €")
        metric_safe.metric("🟢 Safe to Spend", f"{safe_to_spend_f:.2f} €", help="Διαθέσιμο υπόλοιπο μείων τα Πάγια/Λογαριασμούς & Αποταμίευση")

    if filtered_df.empty:
        st.warning("Δεν βρέθηκαν εγγραφές για τη συγκεκριμένη περίοδο.")
        return

    filtered_df["Clean_Amount"] = pd.to_numeric(filtered_df["Ποσό"].astype(str).str.replace(",", "."), errors="coerce").fillna(0.0)
    filtered_df["Ποσό (€)"] = filtered_df["Clean_Amount"]

    # Ταξινόμηση
    if sort_order == "Ημερομηνία (Νεότερες πρώτα)":
        filtered_df = filtered_df.sort_values(by=["Date_Parsed"], ascending=False)
    elif sort_order == "Ημερομηνία (Παλαιότερες πρώτα)":
        filtered_df = filtered_df.sort_values(by=["Date_Parsed"], ascending=True)
    elif sort_order == "Ποσό (Μεγαλύτερα)":
        filtered_df = filtered_df.sort_values(by=["Clean_Amount"], ascending=False)
    elif sort_order == "Ποσό (Μικρότερα)":
        filtered_df = filtered_df.sort_values(by=["Clean_Amount"], ascending=True)

    desired_cols = ["Ημερομηνία", "Περιγραφή", "Τύπος", "Κατηγορία", "Ποσό"]
    available_cols = [c for c in desired_cols if c in filtered_df.columns]

    # PAGINATION (10 εγγραφές ανά σελίδα)
    ITEMS_PER_PAGE = 10
    total_items = len(filtered_df)
    total_pages = max(1, (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

    if "dash_page" not in st.session_state:
        st.session_state["dash_page"] = 1

    if st.session_state["dash_page"] > total_pages:
        st.session_state["dash_page"] = 1

    start_idx = (st.session_state["dash_page"] - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    page_df = filtered_df.iloc[start_idx:end_idx]

    st.table(page_df[available_cols].astype(str))

    # Κουμπιά Σελιδοποίησης
    col_prev, col_info, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.session_state["dash_page"] > 1:
            if st.button("⬅️ Προηγούμενη", key="dash_prev_page", use_container_width=True):
                st.session_state["dash_page"] -= 1
                st.rerun()
    with col_info:
        st.markdown(f"<p style='text-align: center; margin-top: 5px;'><b>Σελίδα {st.session_state['dash_page']} από {total_pages}</b> ({total_items} εγγραφές)</p>", unsafe_allow_html=True)
    with col_next:
        if st.session_state["dash_page"] < total_pages:
            if st.button("Επόμενη ➡️", key="dash_next_page", use_container_width=True):
                st.session_state["dash_page"] += 1
                st.rerun()

    st.markdown("---")

    # --- 3. DROP-DOWN SELECTOR ΓΙΑ ΕΠΙΛΟΓΗ ΔΙΑΓΡΑΜΜΑΤΟΣ ---
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

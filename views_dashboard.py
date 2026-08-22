import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def render_dashboard(worksheet, current_user, t=None):
    # Default fallback αν δεν περαστεί το t
    if t is None:
        t = {}

    st.subheader(t.get("dash_title", "📊 Αναφορές & Analytics"))

    try:
        data = worksheet.get_all_values()
    except Exception as e:
        st.error(f"⚠️ Error fetching data: {e}")
        return

    if not data or len(data) <= 1:
        st.info(t.get("dash_no_data", "Δεν υπάρχουν καταχωρημένα δεδομένα για την παραγωγή αναφορών."))
        return

    raw_headers = data[0]
    clean_headers = [str(h).strip() if str(h).strip() else f"Col_{i+1}" for i, h in enumerate(raw_headers)]
    df = pd.DataFrame(data[1:], columns=clean_headers)

    if "Username" in df.columns:
        df = df[df["Username"] == current_user]

    if df.empty:
        st.info(t.get("dash_no_data_user", "Δεν βρέθηκαν εγγραφές για τον συνδεδεμένο χρήστη."))
        return

    df["Numeric_Amount"] = pd.to_numeric(df["Ποσό"].astype(str).str.replace(",", "."), errors="coerce").fillna(0.0)
    df["Parsed_Date"] = pd.to_datetime(df["Ημερομηνία"], errors="coerce")
    df["Year"] = df["Parsed_Date"].dt.year.fillna(0).astype(int)
    df["Month"] = df["Parsed_Date"].dt.month.fillna(0).astype(int)

    # --- FILTERS ---
    st.markdown(f"### {t.get('dash_filters', '📅 Φίλτρα Χρονικής Περιόδου')}")
    col_f1, col_f2 = st.columns(2)

    years = [t.get("all", "Όλα")] + sorted([y for y in df["Year"].unique() if y != 0], reverse=True)
    with col_f1:
        selected_year = st.selectbox(t.get("dash_year", "Επιλογή Έτους"), years, key="dash_year_select")

    months = [t.get("all", "Όλοι")] + list(range(1, 13))
    with col_f2:
        selected_month = st.selectbox(t.get("dash_month", "Επιλογή Μήνα"), months, key="dash_month_select")

    filtered_df = df.copy()
    if selected_year != t.get("all", "Όλα"):
        filtered_df = filtered_df[filtered_df["Year"] == selected_year]
    if selected_month != t.get("all", "Όλοι"):
        filtered_df = filtered_df[filtered_df["Month"] == selected_month]

    # --- METRICS ---
    total_inc = filtered_df[filtered_df["Τύπος"] == "Έσοδο"]["Numeric_Amount"].sum()
    total_exp = filtered_df[filtered_df["Τύπος"] == "Έξοδο"]["Numeric_Amount"].sum()
    net_bal = total_inc - total_exp

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric(t.get("dash_inc", "💰 Έσοδα Περιόδου"), f"{total_inc:.2f} €")
    col_m2.metric(t.get("dash_exp", "💸 Έξοδα Περιόδου"), f"{total_exp:.2f} €")
    col_m3.metric(t.get("dash_net", "📈 Καθαρό Αποτέλεσμα"), f"{net_bal:.2f} €")

    st.markdown("---")

    # --- CHARTS ---
    col_c1, col_c2 = st.columns(2)

    with col_c1:
        st.markdown(f"#### {t.get('dash_pie_title', '🍩 Κατανομή Εξόδων ανά Κατηγορία')}")
        exp_df = filtered_df[filtered_df["Τύπος"] == "Έξοδο"]
        if not exp_df.empty:
            cat_df = exp_df.groupby("Κατηγορία")["Numeric_Amount"].sum().reset_index()
            fig_pie = px.pie(cat_df, values="Numeric_Amount", names="Κατηγορία", hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.caption(t.get("dash_no_exp", "Δεν υπάρχουν έξοδα για τη συγκεκριμένη περίοδο."))

    with col_c2:
        st.markdown(f"#### {t.get('dash_bar_title', '📊 Μηνιαία Τάση Εσόδων vs Εξόδων')}")
        trend_df = filtered_df.dropna(subset=["Parsed_Date"]).copy()
        if not trend_df.empty:
            trend_df["YearMonth"] = trend_df["Parsed_Date"].dt.strftime("%Y-%m")
            grouped = trend_df.groupby(["YearMonth", "Τύπος"])["Numeric_Amount"].sum().unstack(fill_value=0).reset_index()
            
            fig_bar = go.Figure()
            if "Έσοδο" in grouped.columns:
                fig_bar.add_trace(go.Bar(x=grouped["YearMonth"], y=grouped["Έσοδο"], name=t.get("inc_label", "Έσοδα"), marker_color="green"))
            if "Έξοδο" in grouped.columns:
                fig_bar.add_trace(go.Bar(x=grouped["YearMonth"], y=grouped["Έξοδο"], name=t.get("exp_label", "Έξοδα"), marker_color="red"))
            
            fig_bar.update_layout(barmode="group", xaxis_title=t.get("month", "Μήνας"), yaxis_title="Ποσό (€)")
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.caption(t.get("dash_no_trend", "Δεν υπάρχουν δεδομένα τάσης."))

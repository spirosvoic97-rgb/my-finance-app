import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def render_dashboard(worksheet, current_user, t=None):
    if t is None: t = {}

    st.subheader(t.get("dash_title", "📊 Αναφορές & Analytics"))

    try: data = worksheet.get_all_values()
    except Exception: return

    if not data or len(data) <= 1:
        st.info("Δεν υπάρχουν δεδομένα.")
        return

    raw_headers = data[0]
    clean_headers = [str(h).strip() if str(h).strip() else f"Col_{i+1}" for i, h in enumerate(raw_headers)]
    df = pd.DataFrame(data[1:], columns=clean_headers)

    if "Username" in df.columns: df = df[df["Username"] == current_user]
    if df.empty: return

    df["Numeric_Amount"] = pd.to_numeric(df["Ποσό"].astype(str).str.replace(",", "."), errors="coerce").fillna(0.0)
    df["Parsed_Date"] = pd.to_datetime(df["Ημερομηνία"], errors="coerce")
    df["Year"] = df["Parsed_Date"].dt.year.fillna(0).astype(int)
    df["Month"] = df["Parsed_Date"].dt.month.fillna(0).astype(int)

    # --- FILTERS ---
    st.markdown(f"### {t.get('dash_filters', '📅 Φίλτρα Περιόδου')}")
    col_f1, col_f2 = st.columns(2)
    years = [t.get("all", "Όλα")] + sorted([y for y in df["Year"].unique() if y != 0], reverse=True)
    with col_f1: selected_year = st.selectbox(t.get("dash_year", "Έτος"), years, key="dash_year_select")
    months = [t.get("all", "Όλοι")] + list(range(1, 13))
    with col_f2: selected_month = st.selectbox(t.get("dash_month", "Μήνας"), months, key="dash_month_select")

    filtered_df = df.copy()
    if selected_year != t.get("all", "Όλα"): filtered_df = filtered_df[filtered_df["Year"] == selected_year]
    if selected_month != t.get("all", "Όλοι"): filtered_df = filtered_df[filtered_df["Month"] == selected_month]

    # --- METRICS ---
    total_inc = filtered_df[filtered_df["Τύπος"] == "Έσοδο"]["Numeric_Amount"].sum()
    total_exp = filtered_df[filtered_df["Τύπος"] == "Έξοδο"]["Numeric_Amount"].sum()
    net_bal = total_inc - total_exp

    m1, m2, m3 = st.columns(3)
    m1.metric(t.get("dash_inc", "💰 Έσοδα"), f"{total_inc:.2f} €")
    m2.metric(t.get("dash_exp", "💸 Έξοδα"), f"{total_exp:.2f} €")
    m3.metric(t.get("dash_net", "📈 Καθαρό"), f"{net_bal:.2f} €")

    st.markdown("---")

    # --- 5 CHARTS GRID ---
    # 1 & 2: Pie Charts
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 🍩 Κατανομή Εξόδων")
        exp_df = filtered_df[filtered_df["Τύπος"] == "Έξοδο"]
        if not exp_df.empty:
            st.plotly_chart(px.pie(exp_df.groupby("Κατηγορία")["Numeric_Amount"].sum().reset_index(), values="Numeric_Amount", names="Κατηγορία", hole=0.4), use_container_width=True)
    with c2:
        st.markdown("#### 🍕 Κατανομή Εσόδων")
        inc_df = filtered_df[filtered_df["Τύπος"] == "Έσοδο"]
        if not inc_df.empty:
            st.plotly_chart(px.pie(inc_df.groupby("Κατηγορία")["Numeric_Amount"].sum().reset_index(), values="Numeric_Amount", names="Κατηγορία", hole=0.4), use_container_width=True)

    # 3 & 4: Bar & Line Charts
    c3, c4 = st.columns(2)
    with c3:
        st.markdown("#### 📊 Έσοδα vs Έξοδα ανά Μήνα")
        trend_df = filtered_df.dropna(subset=["Parsed_Date"]).copy()
        if not trend_df.empty:
            trend_df["YM"] = trend_df["Parsed_Date"].dt.strftime("%Y-%m")
            grp = trend_df.groupby(["YM", "Τύπος"])["Numeric_Amount"].sum().unstack(fill_value=0).reset_index()
            fig = go.Figure()
            if "Έσοδο" in grp.columns: fig.add_trace(go.Bar(x=grp["YM"], y=grp["Έσοδο"], name="Έσοδα", marker_color="green"))
            if "Έξοδο" in grp.columns: fig.add_trace(go.Bar(x=grp["YM"], y=grp["Έξοδο"], name="Έξοδα", marker_color="red"))
            st.plotly_chart(fig, use_container_width=True)
    with c4:
        st.markdown("#### 📈 Εξέλιξη Υπολοίπου")
        if not trend_df.empty:
            trend_df = trend_df.sort_values("Parsed_Date")
            trend_df["Signed"] = trend_df.apply(lambda r: r["Numeric_Amount"] if r["Τύπος"] == "Έσοδο" else -r["Numeric_Amount"], axis=1)
            trend_df["CumBalance"] = trend_df["Signed"].cumsum()
            st.plotly_chart(px.line(trend_df, x="Parsed_Date", y="CumBalance", labels={"CumBalance": "Υπόλοιπο (€)"}), use_container_width=True)

    # 5: Top Expenses Bar Chart
    st.markdown("#### 🔝 Top 5 Μεγαλύτερα Έξοδα")
    if not exp_df.empty:
        top_exp = exp_df.sort_values(by="Numeric_Amount", ascending=False).head(5)
        st.plotly_chart(px.bar(top_exp, x="Περιγραφή", y="Numeric_Amount", color="Κατηγορία", text_auto=".2f"), use_container_width=True)

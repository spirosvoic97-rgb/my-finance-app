import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
import base64
from io import BytesIO

st.set_page_config(page_title="Personal Finance Tracker PRO", page_icon="💰", layout="wide")

# --- LOGIN AUTHENTICATION ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.title("🔒 Πρόσβαση στην Εφαρμογή")
        col1, col2 = st.columns([1, 2])
        with col1:
            username = st.text_input("Χρήστης")
            password = st.text_input("Κωδικός", type="password")
            if st.button("Σύνδεση"):
                if "passwords" in st.secrets and username in st.secrets["passwords"]:
                    if password == st.secrets["passwords"][username]:
                        st.session_state["authenticated"] = True
                        st.rerun()
                    else:
                        st.error("❌ Λάθος κωδικός πρόσβασης")
                else:
                    st.error("❌ Λάθος όνομα χρήστη")
        return False
    return True

if check_password():
    STARTING_BALANCE = 672.776

    creds_dict = dict(st.secrets["connections"]["gsheets"])

    # Αποκωδικοποίηση Base64 key
    decoded_key = base64.b64decode(creds_dict["private_key_base64"]).decode("utf-8")
    creds_dict["private_key"] = decoded_key.replace("\\n", "\n")
    del creds_dict["private_key_base64"]

    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    gc = gspread.authorize(credentials)
    
    # Σύνδεση με το Google Sheet
    try:
        sh = gc.open("Finance Tracker Data")
    except gspread.exceptions.SpreadsheetNotFound:
        sh = gc.create("Finance Tracker Data")
        worksheet = sh.get_worksheet(0)
        worksheet.append_row(["Ημερομηνία", "Περιγραφή", "Τύπος", "Κατηγορία", "Ποσό"])

    worksheet = sh.get_worksheet(0)

    # Διάβασμα δεδομένων
    try:
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty and "Ημερομηνία" in df.columns:
            df["Ημερομηνία"] = pd.to_datetime(df["Ημερομηνία"], errors="coerce").dt.strftime("%Y-%m-%d")
            df["Ποσό"] = pd.to_numeric(df["Ποσό"], errors="coerce").fillna(0.0)
            df = df.dropna(subset=["Ημερομηνία"])
    except Exception:
        df = pd.DataFrame(columns=["Ημερομηνία", "Περιγραφή", "Τύπος", "Κατηγορία", "Ποσό"])

    INCOME_CATEGORIES = ["Άλλα Έσοδα / Έκτακτα", "Ιδιαίτερα", "Σχολή Χορού / Ωδείο ΑΜ", "Φροντιστήριο"]
    EXPENSE_CATEGORIES = ["Super Market", "Αποταμίευση", "Διασκέδαση / Έξοδος", "Έκτακτα / Δώρα / Ταξίδια", "Μετακινήσεις", "Πάγια / Λογαριασμοί", "Προσωπικά / Χόμπι", "Επαγγελματικά Έξοδα"]

    BUDGET_LIMITS = {
        "Διασκέδαση / Έξοδος": 300.0,
        "Super Market": 200.0,
        "Προσωπικά / Χόμπι": 150.0
    }

    st.title("📊 Financial Dashboard & Waterfall Tracker PRO")

    # --- SIDEBAR: Φίλτρα & Καταχώρηση ---
    st.sidebar.header("🔍 Φίλτρα Προβολής")
    if not df.empty and "Ημερομηνία" in df.columns:
        temp_years = pd.to_datetime(df["Ημερομηνία"], errors="coerce").dt.year.dropna().astype(int).unique()
        years = sorted(list(temp_years), reverse=True)
        selected_year = st.sidebar.selectbox("Έτος", ["Όλα"] + list(years))
        selected_month = st.sidebar.selectbox("Μήνας", ["Όλοι", 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
    else:
        selected_year, selected_month = "Όλα", "Όλοι"

    st.sidebar.markdown("---")
    st.sidebar.header("➕ Νέα Καταχώρηση")
    entry_type = st.sidebar.radio("Τύπος", ["Έσοδο", "Έξοδο"])
    date = st.sidebar.date_input("Ημερομηνία")
    description = st.sidebar.text_input("Περιγραφή")
    category = st.sidebar.selectbox("Κατηγορία", INCOME_CATEGORIES if entry_type == "Έσοδο" else EXPENSE_CATEGORIES)
    amount = st.sidebar.number_input("Ποσό (€)", min_value=0.0, format="%.2f")

    if st.sidebar.button("Αποθήκευση"):
        worksheet.append_row([str(date), description, entry_type, category, float(amount)], value_input_option="USER_ENTERED")
        st.cache_data.clear()
        st.sidebar.success("Η εγγραφή αποθηκεύτηκε επιτυχώς!")
        st.rerun()

    # --- ΦΙΛΤΡΑΡΙΣΜΑ ΔΕΔΟΜΕΝΩΝ ---
    filtered_df = df.copy()
    if not filtered_df.empty and "Ημερομηνία" in filtered_df.columns:
        temp_dates = pd.to_datetime(filtered_df["Ημερομηνία"], errors="coerce")
        if selected_year != "Όλα":
            filtered_df = filtered_df[temp_dates.dt.year == int(selected_year)]
            temp_dates = pd.to_datetime(filtered_df["Ημερομηνία"], errors="coerce")
        if selected_month != "Όλοι":
            filtered_df = filtered_df[temp_dates.dt.month == int(selected_month)]
            
    total_income = filtered_df[filtered_df["Τύπος"] == "Έσοδο"]["Ποσό"].sum() if not filtered_df.empty else 0.0
    total_expenses = filtered_df[filtered_df["Τύπος"] == "Έξοδο"]["Ποσό"].sum() if not filtered_df.empty else 0.0
    net_month = total_income - total_expenses
        
    overall_income = df[df["Τύπος"] == "Έσοδο"]["Ποσό"].sum() if not df.empty else 0.0
    overall_expenses = df[df["Τύπος"] == "Έξοδο"]["Ποσό"].sum() if not df.empty else 0.0
    final_balance = STARTING_BALANCE + (overall_income - overall_expenses)

    # --- DASHBOARD METRICS ---
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    col1.metric("Αρχικό Ταμείο", f"{STARTING_BALANCE:.2f} €")
    col2.metric("Επιλεγμένα Έσοδα", f"{total_income:.2f} €")
    col3.metric("Επιλεγμένα Έξοδα", f"{total_expenses:.2f} €")
    col4.metric("Συνολικό Υπόλοιπο", f"{final_balance:.2f} €")

    st.markdown("---")

    # --- ALERTS ---
    if not filtered_df.empty:
        exp_by_cat = filtered_df[filtered_df["Τύπος"] == "Έξοδο"].groupby("Κατηγορία")["Ποσό"].sum()
        for cat, limit in BUDGET_LIMITS.items():
            if cat in exp_by_cat and exp_by_cat[cat] > limit:
                st.warning(f"⚠️ **Υπέρβαση Ορίου:** Τα έξοδα στην κατηγορία **{cat}** έφτασαν τα **{exp_by_cat[cat]:.2f} €** (Όριο: {limit:.2f} €)!")

    # --- GRAPHICAL CHARTS (WATERFALL + PIE CHART) ---
    chart_col1, chart_col2 = st.columns([3, 2])

    with chart_col1:
        st.subheader("🌊 Waterfall Analysis")
        if not filtered_df.empty and total_income + total_expenses > 0:
            expense_by_cat = filtered_df[filtered_df["Τύπος"] == "Έξοδο"].groupby("Κατηγορία")["Ποσό"].sum()
            x_list = ["INCOME"] + list(expense_by_cat.index) + ["BALANCE"]
            y_list = [total_income] + list(-expense_by_cat.values) + [0]
            measure_list = ["relative"] + ["relative"] * len(expense_by_cat) + ["total"]

            fig_waterfall = go.Figure(go.Waterfall(
                name="Cashflow", orientation="v",
                measure=measure_list, x=x_list, textposition="outside",
                text=[f"{val:.2f}" if val != 0 else f"{net_month:.2f}" for val in y_list[:-1]] + [f"{net_month:.2f}"],
                y=y_list,
                connector={"line": {"color": "rgb(63, 63, 63)"}},
                decreasing={"marker": {"color": "#EF553B"}},
                increasing={"marker": {"color": "#636EFA"}},
                totals={"marker": {"color": "#7F7F7F"}}
            ))
            fig_waterfall.update_layout(title="Ανάλυση Ταμειακών Ροών", showlegend=False, template="plotly_dark", height=400)
            st.plotly_chart(fig_waterfall, use_container_width=True)
        else:
            st.info("Δεν υπάρχουν δεδομένα για την εμφάνιση του Waterfall Chart.")

    with chart_col2:
        st.subheader("🍕 Κατανομή Εξόδων")
        if not filtered_df.empty and total_expenses > 0:
            exp_df = filtered_df[filtered_df["Τύπος"] == "Έξοδο"]
            fig_pie = px.pie(exp_df, values="Ποσό", names="Κατηγορία", hole=0.4, template="plotly_dark")
            fig_pie.update_layout(height=400)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Δεν υπάρχουν έξοδα στη συγκεκριμένη περίοδο.")

    # --- TABLE & DOWNLOAD ---
    st.subheader("📋 Ιστορικό Εγγραφών")
    if not filtered_df.empty:
        # Επικεφαλίδες Πίνακα
        hcol1, hcol2, hcol3, hcol4, hcol5, hcol6 = st.columns([1.5, 2.5, 1.2, 2.2, 1.2, 0.8])
        hcol1.markdown("**Ημερομηνία**")
        hcol2.markdown("**Περιγραφή**")
        hcol3.markdown("**Τύπος**")
        hcol4.markdown("**Κατηγορία**")
        hcol5.markdown("**Ποσό (€)**")
        hcol6.markdown("**Ενέργεια**")
        st.markdown("---")

        # Εμφάνιση κάθε εγγραφής σε ξεχωριστή γραμμή με κουμπί διαγραφής
        for idx, row in filtered_df.iterrows():
            rcol1, rcol2, rcol3, rcol4, rcol5, rcol6 = st.columns([1.5, 2.5, 1.2, 2.2, 1.2, 0.8])
            rcol1.write(str(row["Ημερομηνία"]))
            rcol2.write(row["Περιγραφή"] if row["Περιγραφή"] else "-")
            rcol3.write(row["Τύπος"])
            rcol4.write(row["Κατηγορία"])
            rcol5.write(f"{row['Ποσό']:.2f} €")
            
            # Κουμπί Διαγραφής δίπλα σε κάθε εγγραφή
            if rcol6.button("🗑️", key=f"del_{idx}"):
            # Υπολογισμός πραγματικής γραμμής στο Google Sheet
            row_to_delete = int(idx) + 2
            worksheet.delete_rows(row_to_delete)
            st.cache_data.clear()
            st.success("Η εγγραφή διαγράφηκε!")
            st.rerun()
    else:
        st.info("Δεν υπάρχουν εγγραφές για προβολή.")

    st.markdown("---")
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Data')
    excel_data = output.getvalue()

    st.download_button(
        label="📥 Download Excel Report",
        data=excel_data,
        file_name="finance_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

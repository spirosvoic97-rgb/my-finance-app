import streamlit as st
import pandas as pd
import plotly.graph_objects as go
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

# Αποκωδικοποίηση του Base64 private key
decoded_key = base64.b64decode(creds_dict["private_key_base64"]).decode("utf-8")
creds_dict["private_key"] = decoded_key

scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
gc = gspread.authorize(credentials)

    # Σύνδεση με το Google Sheet
    sh = gc.open_by_url(st.secrets["connections"]["gsheets"]["spreadsheet"])
    worksheet = sh.get_worksheet(0)

    # Διάβασμα δεδομένων
    try:
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty and "Ημερομηνία" in df.columns:
            df["Ημερομηνία"] = pd.to_datetime(df["Ημερομηνία"])
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

    # Sidebar: Φίλτρα & Καταχώρηση
    st.sidebar.header("🔍 Φίλτρα Προβολής")
    if not df.empty and "Ημερομηνία" in df.columns:
        years = sorted(list(df["Ημερομηνία"].dt.year.unique()), reverse=True)
        selected_year = st.sidebar.selectbox("Έτος", ["Όλα"] + years)
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
        worksheet.append_row([str(date), description, entry_type, category, amount])
        st.sidebar.success("Η εγγραφή αποθηκεύτηκε επιτυχώς στο Google Sheet!")
        st.rerun()

    # Φιλτράρισμα Δεδομένων
    filtered_df = df.copy()
    if not filtered_df.empty and "Ημερομηνία" in filtered_df.columns:
        if selected_year != "Όλα":
            filtered_df = filtered_df[filtered_df["Ημερομηνία"].dt.year == int(selected_year)]
        if selected_month != "Όλοι":
            filtered_df = filtered_df[filtered_df["Ημερομηνία"].dt.month == int(selected_month)]

    total_income = filtered_df[filtered_df["Τύπος"] == "Έσοδο"]["Ποσό"].sum() if not filtered_df.empty else 0.0
    total_expenses = filtered_df[filtered_df["Τύπος"] == "Έξοδο"]["Ποσό"].sum() if not filtered_df.empty else 0.0
    net_month = total_income - total_expenses
    
    overall_income = df[df["Τύπος"] == "Έσοδο"]["Ποσό"].sum() if not df.empty else 0.0
    overall_expenses = df[df["Τύπος"] == "Έξοδο"]["Ποσό"].sum() if not df.empty else 0.0
    final_balance = STARTING_BALANCE + (overall_income - overall_expenses)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Αρχικό Ταμείο", f"{STARTING_BALANCE:.2f} €")
    col2.metric("Επιλεγμένα Έσοδα", f"{total_income:.2f} €")
    col3.metric("Επιλεγμένα Έξοδα", f"{total_expenses:.2f} €")
    col4.metric("Συνολικό Υπόλοιπο (Balance)", f"{final_balance:.2f} €")

    st.markdown("---")

    # Ειδοποιήσεις Προϋπολογισμού (Alerts)
    if not filtered_df.empty:
        exp_by_cat = filtered_df[filtered_df["Τύπος"] == "Έξοδο"].groupby("Κατηγορία")["Ποσό"].sum()
        for cat, limit in BUDGET_LIMITS.items():
            if cat in exp_by_cat and exp_by_cat[cat] > limit:
                st.warning(f"⚠️ **Υπέρβαση Ορίου:** Τα έξοδα στην κατηγορία **{cat}** έφτασαν τα **{exp_by_cat[cat]:.2f} €** (Όριο: {limit:.2f} €)!")

    # Waterfall Chart
    st.subheader("🌊 Waterfall Analysis")
    if not filtered_df.empty:
        expense_by_cat = filtered_df[filtered_df["Τύπος"] == "Έξοδο"].groupby("Κατηγορία")["Ποσό"].sum()
        x_list = ["INCOME"] + list(expense_by_cat.index) + ["BALANCE"]
        y_list = [total_income] + list(-expense_by_cat.values) + [0]
        measure_list = ["relative"] + ["relative"] * len(expense_by_cat) + ["total"]

        fig = go.Figure(go.Waterfall(
            name="Cashflow", orientation="v",
            measure=measure_list, x=x_list, textposition="outside",
            text=[f"{val:.2f}" if val != 0 else f"{net_month:.2f}" for val in y_list[:-1]] + [f"{net_month:.2f}"],
            y=y_list,
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            decreasing={"marker": {"color": "#EF553B"}},
            increasing={"marker": {"color": "#636EFA"}},
            totals={"marker": {"color": "#7F7F7F"}}
        ))
        fig.update_layout(title="Ανάλυση Εσόδων - Εξόδων", showlegend=False, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

    # Table & Download
    st.subheader("📋 Ιστορικό Εγγραφών")
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Data')
    excel_data = output.getvalue()
    
    st.download_button(label="📥 Download Excel Report", data=excel_data, file_name="finance_report.xlsx", mime="application/vnd.ms-excel")
    st.dataframe(filtered_df, use_container_width=True)

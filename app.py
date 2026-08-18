import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Personal Finance Tracker", page_icon="💰", layout="wide")

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
    DATA_FILE = "finance_data.csv"
    STARTING_BALANCE = 672.776

    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
    else:
        df = pd.DataFrame(columns=["Ημερομηνία", "Περιγραφή", "Τύπος", "Κατηγορία", "Ποσό"])

    INCOME_CATEGORIES = [
        "Άλλα Έσοδα / Έκτακτα", 
        "Ιδιαίτερα", 
        "Σχολή Χορού / Ωδείο ΑΜ", 
        "Φροντιστήριο"
    ]

    EXPENSE_CATEGORIES = [
        "Super Market", 
        "Αποταμίευση", 
        "Διασκέδαση / Έξοδος", 
        "Έκτακτα / Δώρα / Ταξίδια", 
        "Μετακινήσεις", 
        "Πάγια / Λογαριασμοί", 
        "Προσωπικά / Χόμπι", 
        "Επαγγελματικά Έξοδα"
    ]

    st.title("📊 Financial Dashboard & Waterfall Tracker")

    # Φόρμα Καταχώρησης
    st.sidebar.header("➕ Νέα Καταχώρηση")
    entry_type = st.sidebar.radio("Τύπος", ["Έσοδο", "Έξοδο"])
    date = st.sidebar.date_input("Ημερομηνία")
    description = st.sidebar.text_input("Περιγραφή")

    if entry_type == "Έσοδο":
        category = st.sidebar.selectbox("Κατηγορία Εσόδου", INCOME_CATEGORIES)
    else:
        category = st.sidebar.selectbox("Κατηγορία Εξόδου", EXPENSE_CATEGORIES)

    amount = st.sidebar.number_input("Ποσό (€)", min_value=0.0, format="%.2f")

    if st.sidebar.button("Αποθήκευση"):
        new_data = pd.DataFrame([{
            "Ημερομηνία": date,
            "Περιγραφή": description,
            "Τύπος": entry_type,
            "Κατηγορία": category,
            "Ποσό": amount
        }])
        df = pd.concat([df, new_data], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        st.sidebar.success("Η εγγραφή αποθηκεύτηκε!")
        st.rerun()

    total_income = df[df["Τύπος"] == "Έσοδο"]["Ποσό"].sum() if not df.empty else 0.0
    total_expenses = df[df["Τύπος"] == "Έξοδο"]["Ποσό"].sum() if not df.empty else 0.0
    net_month = total_income - total_expenses
    final_balance = STARTING_BALANCE + net_month

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Αρχικό Ταμείο", f"{STARTING_BALANCE:.2f} €")
    col2.metric("Συνολικά Έσοδα", f"{total_income:.2f} €")
    col3.metric("Συνολικά Έξοδα", f"{total_expenses:.2f} €")
    col4.metric("Τελικό Υπόλοιπο (Balance)", f"{final_balance:.2f} €")

    st.markdown("---")
    st.subheader("🌊 Waterfall Analysis")

    if not df.empty:
        expense_by_cat = df[df["Τύπος"] == "Έξοδο"].groupby("Κατηγορία")["Ποσό"].sum()
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
        fig.update_layout(title="Ανάλυση Εσόδων - Εξόδων & Καθαρού Αποτελέσματος", showlegend=False, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 Ιστορικό Εγγραφών")
    st.dataframe(df, use_container_width=True)

import streamlit as st
import pandas as pd
from config import ICON_URL, get_sheets_connection
from auth import render_login_signup
from views_dashboard import render_dashboard
from views_entry import render_entry
from views_profile import render_profile

# 1. Page Config
st.set_page_config(page_title="FinancePRO", page_icon=ICON_URL, layout="wide")

# 2. Get Google Sheets Connection
worksheet, users_sheet = get_sheets_connection()

# 3. Authentication
if render_login_signup(users_sheet):
    current_user = st.session_state.get("current_user", "Guest")
    user_email = st.session_state.get("user_email", "")
    STARTING_BALANCE = st.session_state.get("starting_balance", 0.00)

    # Bulletproof Data Loading & User Filtering
    try:
        raw_rows = worksheet.get_all_values()
        if len(raw_rows) > 1:
            header = raw_rows[0]
            clean_rows = [header] + [r for r in raw_rows[1:] if len(r) > 0 and str(r[0]).strip() != "Ημερομηνία"]
            df_raw = pd.DataFrame(clean_rows[1:], columns=clean_rows[0])
            df_raw = df_raw.loc[:, ~df_raw.columns.duplicated()].copy()

            if not df_raw.empty:
                if "Ποσό" in df_raw.columns:
                    df_raw["Ποσό"] = pd.to_numeric(df_raw["Ποσό"], errors="coerce").fillna(0.0)
                
                if "Username" in df_raw.columns:
                    df_raw["Username_clean"] = df_raw["Username"].astype(str).str.strip().str.lower()
                    user_match = df_raw[df_raw["Username_clean"] == current_user.lower()].copy()
                    df = user_match if not user_match.empty else pd.DataFrame(columns=header)
                else:
                    df = df_raw.copy()
            else:
                df = pd.DataFrame(columns=["Ημερομηνία", "Περιγραφή", "Τύπος", "Κατηγορία", "Ποσό", "Επαναλαμβανόμενο", "Username"])
        else:
            df = pd.DataFrame(columns=["Ημερομηνία", "Περιγραφή", "Τύπος", "Κατηγορία", "Ποσό", "Επαναλαμβανόμενο", "Username"])
    except Exception as e:
        st.error(f"⚠️ Σφάλμα φόρτωσης δεδομένων: {e}")
        df = pd.DataFrame(columns=["Ημερομηνία", "Περιγραφή", "Τύπος", "Κατηγορία", "Ποσό", "Επαναλαμβανόμενο", "Username"])

    # Sidebar
    st.sidebar.markdown(f"👤 **{current_user}**")
    if st.sidebar.button("🚪 Αποσύνδεση", key="side_logout"):
        st.session_state["authenticated"] = False
        st.session_state["current_user"] = ""
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Φίλτρα Προβολής")
    dt_series = pd.to_datetime(df["Ημερομηνία"], errors="coerce") if not df.empty and "Ημερομηνία" in df.columns else pd.Series(dtype='datetime64[ns]')
    valid_years = dt_series.dt.year.dropna().astype(int).unique() if not dt_series.empty else []
    years = sorted(list(valid_years), reverse=True)
    
    selected_year = st.sidebar.selectbox("Έτος", ["Όλα"] + list(years))
    selected_month = st.sidebar.selectbox("Μήνας", ["Όλοι", 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
    search_query = st.sidebar.text_input("🔎 Αναζήτηση Περιγραφής", "")

    # Theme Injection
    theme = st.session_state.get("theme", "Dark Mode 🌙")
    if theme == "Light Mode ☀️":
        plotly_template, chart_bg, chart_font_color, chart_grid_color, card_bg = "plotly_white", "#FFFFFF", "#111111", "#D1D5DB", "#F8F9FA"
        st.markdown("<style>header[data-testid='stHeader'] { visibility: hidden !important; height: 0px !important; } footer { visibility: hidden !important; }</style>", unsafe_allow_html=True)
    else:
        plotly_template, chart_bg, chart_font_color, chart_grid_color, card_bg = "plotly_dark", "#11151C", "#FFFFFF", "#333333", "#1A1F2C"
        st.markdown("<style>header[data-testid='stHeader'] { visibility: hidden !important; height: 0px !important; } footer { visibility: hidden !important; }</style>", unsafe_allow_html=True)

    # Navigation
    nav_selected = st.radio("Navigation", ["📊 Dashboard", "➕ Καταχώρηση", "⚙️ Προφίλ"], horizontal=True, label_visibility="collapsed")

    if "Dashboard" in nav_selected:
        render_dashboard(df, worksheet, current_user, STARTING_BALANCE, selected_year, selected_month, search_query, plotly_template, chart_bg, chart_font_color, chart_grid_color, card_bg)
    elif "Καταχώρηση" in nav_selected:
        render_entry(worksheet, current_user)
    elif "Προφίλ" in nav_selected:
        render_profile(users_sheet, current_user, user_email, STARTING_BALANCE, df, worksheet, theme)

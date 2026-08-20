import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
import base64
from io import BytesIO
import datetime
import calendar
import re
import hashlib
import json
from PIL import Image

# 1. Favicon στο Tab του Browser
ICON_URL = "https://raw.githubusercontent.com/spirosvoic97-rgb/my-finance-app/main/icon.png"

st.set_page_config(
    page_title="FinancePRO",
    page_icon=ICON_URL,
    layout="wide"
)

# --- HELPER FUNCTIONS ---
def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hash(password, hashed_text):
    return make_hash(password) == hashed_text

# --- GOOGLE SHEETS SETUP ---
creds_dict = dict(st.secrets["connections"]["gsheets"])
decoded_key = base64.b64decode(creds_dict["private_key_base64"]).decode("utf-8")
creds_dict["private_key"] = decoded_key.replace("\\n", "\n")
del creds_dict["private_key_base64"]

scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
gc = gspread.authorize(credentials)

try:
    sh = gc.open("Finance Tracker Data")
except gspread.exceptions.SpreadsheetNotFound:
    sh = gc.create("Finance Tracker Data")

try:
    worksheet = sh.worksheet("Data")
except gspread.exceptions.WorksheetNotFound:
    worksheet = sh.get_worksheet(0)
    worksheet.update_title("Data")
    worksheet.append_row(["Ημερομηνία", "Περιγραφή", "Τύπος", "Κατηγορία", "Ποσό", "Επαναλαμβανόμενο", "Username"])

try:
    users_sheet = sh.worksheet("Users")
except gspread.exceptions.WorksheetNotFound:
    users_sheet = sh.add_worksheet(title="Users", rows="100", cols="5")
    users_sheet.append_row(["Username", "PasswordHash", "CreatedAt", "Email", "StartingBalance"])

# --- AUTHENTICATION SYSTEM ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.title("🔒 FinancePRO")
        tab_login, tab_signup = st.tabs(["🔑 Σύνδεση", "📝 Εγγραφή Νέου Χρήστη"])
        
        with tab_login:
            col1, col2 = st.columns([1, 2])
            with col1:
                username = st.text_input("Χρήστης", key="login_user")
                password = st.text_input("Κωδικός", type="password", key="login_pass")
                if st.button("Σύνδεση", key="login_btn"):
                    secrets_valid = False
                    if "passwords" in st.secrets and username.strip() in st.secrets["passwords"]:
                        if password == st.secrets["passwords"][username.strip()]:
                            secrets_valid = True

                    sheet_valid = False
                    user_email = ""
                    user_starting_bal = 0.00
                    try:
                        users_data = users_sheet.get_all_records()
                        for u in users_data:
                            if str(u.get("Username", "")).strip().lower() == username.strip().lower() and check_hash(password, str(u.get("PasswordHash", ""))):
                                sheet_valid = True
                                user_email = str(u.get("Email", ""))
                                try:
                                    user_starting_bal = float(u.get("StartingBalance", 0.00))
                                except Exception:
                                    user_starting_bal = 0.00
                                break
                    except Exception:
                        pass

                    if secrets_valid or sheet_valid:
                        st.session_state["authenticated"] = True
                        st.session_state["current_user"] = username.strip()
                        st.session_state["user_email"] = user_email
                        st.session_state["starting_balance"] = user_starting_bal
                        st.session_state["theme"] = "Dark Mode 🌙"
                        st.session_state["active_nav"] = "📊"
                        st.success("✅ Επιτυχής σύνδεση!")
                        st.rerun()
                    else:
                        st.error("❌ Λάθος όνομα χρήστη ή κωδικός πρόσβασης")
                        
        with tab_signup:
            col1, col2 = st.columns([1, 2])
            with col1:
                new_username = st.text_input("Νέο Όνομα Χρήστη", key="signup_user")
                new_email = st.text_input("Email (Προαιρετικό)", key="signup_email")
                init_bal = st.number_input("Αρχικό Ταμείο (€)", value=0.00, step=50.00, key="signup_init_bal")
                new_password = st.text_input("Νέος Κωδικός", type="password", key="signup_pass")
                confirm_password = st.text_input("Επιβεβαίωση Κωδικού", type="password", key="signup_confirm")
                
                if st.button("Δημιουργία Λογαριασμού", key="signup_btn"):
                    if not new_username or not new_password:
                        st.warning("⚠️ Παρακαλώ συμπλήρωσε όλα τα πεδία.")
                    elif new_password != confirm_password:
                        st.error("❌ Οι κωδικοί πρόσβασης δεν ταιριάζουν!")
                    elif len(new_password) < 4:
                        st.warning("⚠️ Ο κωδικός πρέπει να έχει τουλάχιστον 4 χαρακτήρες.")
                    else:
                        existing_users = []
                        try:
                            users_data = users_sheet.get_all_records()
                            existing_users = [str(u.get("Username", "")).strip().lower() for u in users_data]
                        except Exception:
                            pass

                        if new_username.strip().lower() in existing_users:
                            st.error("❌ Το όνομα χρήστη υπάρχει ήδη! Διάλεξε άλλο.")
                        else:
                            pass_hash = make_hash(new_password)
                            created_at = str(datetime.date.today())
                            users_sheet.append_row([new_username.strip(), pass_hash, created_at, new_email, float(init_bal)])
                            st.success("🎉 Ο λογαριασμός δημιουργήθηκε επιτυχώς! Μπορείς τώρα να συνδεθείς.")
        return False
    return True

if check_password():
    current_user = st.session_state.get("current_user", "Guest")
    user_email = st.session_state.get("user_email", "")
    STARTING_BALANCE = st.session_state.get("starting_balance", 0.00)

    # --- AUTO-CLEANUP & BULLETPROOF DATA LOADING ---
    try:
        raw_rows = worksheet.get_all_values()
        if len(raw_rows) > 1:
            header = raw_rows[0]
            clean_rows = [header]
            has_deleted = False
            
            # Έλεγχος & αφαίρεση διπλότυπων επικεφαλίδων στο Google Sheet
            for row_idx, row in enumerate(raw_rows[1:], start=2):
                if len(row) > 0 and str(row[0]).strip() == "Ημερομηνία":
                    try:
                        worksheet.delete_rows(row_idx)
                        has_deleted = True
                    except Exception:
                        pass
                else:
                    clean_rows.append(row)
            
            # Δημιουργία DataFrame από τις καθαρές εγγραφές
            df_raw = pd.DataFrame(clean_rows[1:], columns=clean_rows[0])
            
            if not df_raw.empty:
                if "Ποσό" in df_raw.columns:
                    df_raw["Ποσό"] = pd.to_numeric(df_raw["Ποσό"], errors="coerce").fillna(0.0)
                
                if "Username" in df_raw.columns:
                    df_raw["Username_clean"] = df_raw["Username"].astype(str).str.strip().str.lower()
                    user_match = df_raw[df_raw["Username_clean"] == current_user.lower()].copy()
                    df = user_match if not user_match.empty else df_raw.copy()
                else:
                    df = df_raw.copy()
            else:
                df = pd.DataFrame(columns=["Ημερομηνία", "Περιγραφή", "Τύπος", "Κατηγορία", "Ποσό", "Επαναλαμβανόμενο", "Username"])
        else:
            df = pd.DataFrame(columns=["Ημερομηνία", "Περιγραφή", "Τύπος", "Κατηγορία", "Ποσό", "Επαναλαμβανόμενο", "Username"])
    except Exception:
        df = pd.DataFrame(columns=["Ημερομηνία", "Περιγραφή", "Τύπος", "Κατηγορία", "Ποσό", "Επαναλαμβανόμενο", "Username"])

    INCOME_CATEGORIES = ["Άλλα Έσοδα / Έκτακτα", "Ιδιαίτερα", "Σχολή Χορού / Ωδείο ΑΜ", "Φροντιστήριο"]
    EXPENSE_CATEGORIES = ["Super Market", "Αποταμίευση", "Διασκέδαση / Έξοδος", "Έκτακτα / Δώρα / Ταξίδια", "Μετακινήσεις", "Πάγια / Λογαριασμοί", "Προσωπικά / Χόμπι", "Επαγγελματικά Έξοδα"]

    # --- SIDEBAR: ΦΙΛΤΡΑ ---
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

    # Theme CSS Injection
    theme = st.session_state.get("theme", "Dark Mode 🌙")
    if theme == "Light Mode ☀️":
        plotly_template = "plotly_white"
        chart_bg, chart_font_color, chart_grid_color = "#FFFFFF", "#111111", "#D1D5DB"
        card_bg = "#F8F9FA"
        st.markdown("""
            <style>
            .stApp, [data-testid="stSidebar"], [data-testid="stHeader"], [data-testid="stAppToolbar"], header { background-color: #FFFFFF !important; color: #111111 !important; }
            [data-testid="stHeader"] img, [data-testid="stAppToolbar"] img, [data-testid="stHeader"] svg, [data-testid="stAppToolbar"] svg, header svg, button[kind="header"] svg { filter: invert(1) !important; }
            h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, [data-testid="stMetricValue"], [data-testid="stMetricLabel"] { color: #111111 !important; }
            input, select, textarea, div[role="combobox"], [data-baseweb="select"] { background-color: #FFFFFF !important; color: #111111 !important; border: 1px solid #111111 !important; }
            .stButton > button, button[aria-haspopup="dialog"], .stDownloadButton > button { background-color: #FFFFFF !important; color: #111111 !important; border: 1px solid #111111 !important; font-weight: bold !important; }
            hr { border-color: #E0E0E0 !important; }
            </style>
        """, unsafe_allow_html=True)
    else:
        plotly_template = "plotly_dark"
        chart_bg, chart_font_color, chart_grid_color = "#11151C", "#FFFFFF", "#333333"
        card_bg = "#1A1F2C"

    # CSS Injection για Ultra-compact Popovers & Rows
    st.markdown("""
        <style>
        div[data-testid="stPopover"] { display: inline-block !important; margin: 0 !important; }
        div[data-testid="stPopover"] > button { padding: 1px 5px !important; height: 26px !important; min-height: 26px !important; font-size: 11px !important; line-height: 1 !important; border-radius: 6px !important; }
        </style>
    """, unsafe_allow_html=True)

    # TOP TABS / NAVIGATION
    nav_selected = st.radio("Navigation", ["📊 Dashboard", "➕ Καταχώρηση", "⚙️ Προφίλ"], horizontal=True, label_visibility="collapsed")
    
    # -------------------------------------------------------------------
    # ENOTHTA 1: DASHBOARD
    # -------------------------------------------------------------------
    if "Dashboard" in nav_selected:
        filtered_df = df.copy()
        if not filtered_df.empty and "Ημερομηνία" in filtered_df.columns:
            temp_dates = pd.to_datetime(filtered_df["Ημερομηνία"], errors="coerce")
            if selected_year != "Όλα":
                filtered_df = filtered_df[temp_dates.dt.year == int(selected_year)]
                temp_dates = pd.to_datetime(filtered_df["Ημερομηνία"], errors="coerce")
            if selected_month != "Όλοι":
                filtered_df = filtered_df[temp_dates.dt.month == int(selected_month)]
            if search_query:
                filtered_df = filtered_df[filtered_df["Περιγραφή"].astype(str).str.contains(search_query, case=False, na=False)]
                
        total_income = filtered_df[filtered_df["Τύπος"] == "Έσοδο"]["Ποσό"].sum() if not filtered_df.empty else 0.0
        total_expenses = filtered_df[filtered_df["Τύπος"] == "Έξοδο"]["Ποσό"].sum() if not filtered_df.empty else 0.0
        net_month = total_income - total_expenses
            
        overall_income = df[df["Τύπος"] == "Έσοδο"]["Ποσό"].sum() if not df.empty else 0.0
        overall_expenses = df[df["Τύπος"] == "Έξοδο"]["Ποσό"].sum() if not df.empty else 0.0
        final_balance = STARTING_BALANCE + (overall_income - overall_expenses)

        # Safe-to-Spend
        now = datetime.date.today()
        days_in_month = calendar.monthrange(now.year, now.month)[1]
        days_remaining = (days_in_month - now.day) + 1
        safe_to_spend_daily = (final_balance / days_remaining) if final_balance > 0 and days_remaining > 0 else 0.0

        # TRADING 212 HEADER
        st.markdown(
            f"""
            <div style="background-color: {card_bg}; padding: 15px; border-radius: 12px; margin-bottom: 15px; text-align: center; border: 1px solid #333333;">
                <div style="font-size: 11px; color: #888888; text-transform: uppercase; letter-spacing: 1px;">Συνολικό Υπόλοιπο (Αρχικό: {STARTING_BALANCE:.2f} €)</div>
                <div style="font-size: 34px; font-weight: bold; margin: 2px 0; color: {chart_font_color};">{final_balance:,.2f} €</div>
                <div style="font-size: 12px; margin-top: 6px; display: flex; justify-content: space-around;">
                    <span style="color: #00CC96;">🟢 {total_income:,.2f} €</span>
                    <span style="color: #EF553B;">🔴 {total_expenses:,.2f} €</span>
                    <span style="color: #AB63FA;">💡 {safe_to_spend_daily:,.2f} €/ημ</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        if safe_to_spend_daily < 10.0 and final_balance > 0:
            st.error(f"🚨 **Alert:** Safe-to-Spend στα **{safe_to_spend_daily:.2f} € / ημέρα**!")

        # --- ΜΗΝΙΑΙΑ ΣΥΓΚΡΙΣΗ ---
        if not df.empty:
            df['dt_temp'] = pd.to_datetime(df['Ημερομηνία'], errors='coerce')
            curr_m = now.month
            curr_y = now.year
            prev_m = 12 if curr_m == 1 else curr_m - 1
            prev_y = curr_y - 1 if curr_m == 1 else curr_y

            curr_m_income = df[(df['dt_temp'].dt.month == curr_m) & (df['dt_temp'].dt.year == curr_y) & (df['Τύπος'] == 'Έσοδο')]['Ποσό'].sum()
            curr_m_exp = df[(df['dt_temp'].dt.month == curr_m) & (df['dt_temp'].dt.year == curr_y) & (df['Τύπος'] == 'Έξοδο')]['Ποσό'].sum()

            prev_m_income = df[(df['dt_temp'].dt.month == prev_m) & (df['dt_temp'].dt.year == prev_y) & (df['Τύπος'] == 'Έσοδο')]['Ποσό'].sum()
            prev_m_exp = df[(df['dt_temp'].dt.month == prev_m) & (df['dt_temp'].dt.year == prev_y) & (df['Τύπος'] == 'Έξοδο')]['Ποσό'].sum()

            inc_change = ((curr_m_income - prev_m_income) / prev_m_income * 100) if prev_m_income > 0 else 0.0
            exp_change = ((curr_m_exp - prev_m_exp) / prev_m_exp * 100) if prev_m_exp > 0 else 0.0

            with st.expander("📊 Σύγκριση με Προηγούμενο Μήνα"):
                m_col1, m_col2 = st.columns(2)
                m_col1.metric("Έσοδα Μήνα", f"{curr_m_income:.2f} €", delta=f"{inc_change:+.1f}% vs προηγ. μήνα")
                m_col2.metric("Έξοδα Μήνα", f"{curr_m_exp:.2f} €", delta=f"{exp_change:+.1f}% vs προηγ. μήνα", delta_color="inverse")

        # Charts
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
                    textfont=dict(color=chart_font_color, size=11),
                    y=y_list,
                    connector={"line": {"color": "rgb(63, 63, 63)"}},
                    decreasing={"marker": {"color": "#EF553B"}},
                    increasing={"marker": {"color": "#636EFA"}},
                    totals={"marker": {"color": "#7F7F7F"}}
                ))
                fig_waterfall.update_layout(
                    showlegend=False, template=plotly_template, paper_bgcolor=chart_bg, plot_bgcolor=chart_bg, font=dict(color=chart_font_color), height=300,
                    xaxis=dict(fixedrange=True, color=chart_font_color, gridcolor=chart_grid_color),
                    yaxis=dict(fixedrange=True, color=chart_font_color, gridcolor=chart_grid_color)
                )
                st.plotly_chart(fig_waterfall, use_container_width=True, config={'scrollZoom': False, 'displayModeBar': False})
            else:
                st.info("Δεν υπάρχουν δεδομένα.")

        with chart_col2:
            st.subheader("🍕 Κατανομή Εξόδων")
            if not filtered_df.empty and total_expenses > 0:
                exp_df = filtered_df[filtered_df["Τύπος"] == "Έξοδο"]
                fig_pie = px.pie(exp_df, values="Ποσό", names="Κατηγορία", hole=0.4, template=plotly_template)
                fig_pie.update_layout(height=300, paper_bgcolor=chart_bg, plot_bgcolor=chart_bg, font=dict(color=chart_font_color), legend=dict(font=dict(color=chart_font_color)))
                fig_pie.update_traces(textfont=dict(color=chart_font_color))
                st.plotly_chart(fig_pie, use_container_width=True, config={'scrollZoom': False, 'displayModeBar': False})
            else:
                st.info("Δεν υπάρχουν έξοδα.")

        # Line Chart
        st.subheader("📈 Μηνιαία Τάση")
        if not df.empty:
            trend_df = df.copy()
            trend_df["dt"] = pd.to_datetime(trend_df["Ημερομηνία"], errors="coerce")
            trend_df = trend_df.dropna(subset=["dt"])
            trend_df["Sort_Key"] = trend_df["dt"].dt.strftime("%Y-%m")
            trend_df["Μήνας"] = trend_df["dt"].dt.strftime("%b %Y")
            
            monthly_summary = trend_df.groupby(["Sort_Key", "Μήνας", "Τύπος"])["Ποσό"].sum().reset_index()
            if not monthly_summary.empty:
                pivot_df = monthly_summary.pivot(index=["Sort_Key", "Μήνας"], columns="Τύπος", values="Ποσό").fillna(0.0).reset_index()
                if "Έσοδο" not in pivot_df.columns: pivot_df["Έσοδο"] = 0.0
                if "Έξοδο" not in pivot_df.columns: pivot_df["Έξοδο"] = 0.0
                pivot_df["Καθαρό (Net)"] = pivot_df["Έσοδο"] - pivot_df["Έξοδο"]
                pivot_df = pivot_df.sort_values("Sort_Key")

                fig_line = go.Figure()
                fig_line.add_trace(go.Scatter(x=pivot_df["Μήνας"], y=pivot_df["Έσοδο"], mode='lines+markers', name='Έσοδο', line=dict(color='#00CC96', width=3)))
                fig_line.add_trace(go.Scatter(x=pivot_df["Μήνας"], y=pivot_df["Έξοδο"], mode='lines+markers', name='Έξοδο', line=dict(color='#EF553B', width=3)))
                fig_line.add_trace(go.Scatter(x=pivot_df["Μήνας"], y=pivot_df["Καθαρό (Net)"], mode='lines+markers', name='Καθαρό (Net)', line=dict(color='#AB63FA', width=2, dash='dash')))

                fig_line.update_xaxes(type='category', fixedrange=True, color=chart_font_color, gridcolor=chart_grid_color)
                fig_line.update_yaxes(fixedrange=True, color=chart_font_color, gridcolor=chart_grid_color)
                fig_line.update_layout(height=300, template=plotly_template, paper_bgcolor=chart_bg, plot_bgcolor=chart_bg, font=dict(color=chart_font_color), legend=dict(font=dict(color=chart_font_color)))
                st.plotly_chart(fig_line, use_container_width=True, config={'scrollZoom': False, 'displayModeBar': False})

        st.markdown("---")

        # --- ΙΣΤΟΡΙΚΟ ΕΓΓΡΑΦΩΝ ---
        st.subheader("📋 Ιστορικό Εγγραφών")
        if not filtered_df.empty:
            sorted_history = filtered_df.sort_values(by="Ημερομηνία", ascending=False).reset_index(drop=True)
            
            items_per_page = 10
            total_items = len(sorted_history)
            total_pages = (total_items - 1) // items_per_page + 1

            if "history_page" not in st.session_state:
                st.session_state["history_page"] = 1

            current_page = st.session_state["history_page"]
            if current_page > total_pages:
                current_page = total_pages
                st.session_state["history_page"] = total_pages

            start_idx = (current_page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            page_items = sorted_history.iloc[start_idx:end_idx]

            for idx, row in page_items.iterrows():
                amt_color = "#00CC96" if row["Τύπος"] == "Έσοδο" else "#EF553B"
                desc_txt = f" ({row['Περιγραφή']})" if row['Περιγραφή'] else ""
                
                c_info, c_acts = st.columns([3, 1])
                
                with c_info:
                    st.markdown(f"<div style='font-size: 13px; line-height: 1.2;'><b>{row['Ημερομηνία']}</b> <span style='color:#888888;'>{row['Κατηγορία']}{desc_txt}</span></div>", unsafe_allow_html=True)
                
                with c_acts:
                    a1, a2, a3 = st.columns([1, 1, 2])
                    with a1:
                        with st.popover("✏️"):
                            st.write("Επεξεργασία")
                            edit_date = st.date_input("Ημερομηνία", pd.to_datetime(row["Ημερομηνία"]), key=f"edit_date_{idx}")
                            edit_type = st.radio("Τύπος", ["Έσοδο", "Έξοδο"], index=0 if row["Τύπος"] == "Έσοδο" else 1, key=f"edit_type_{idx}")
                            edit_desc = st.text_input("Περιγραφή", value=row["Περιγραφή"], key=f"edit_desc_{idx}")
                            cats = INCOME_CATEGORIES if edit_type == "Έσοδο" else EXPENSE_CATEGORIES
                            cat_index = cats.index(row["Κατηγορία"]) if row["Κατηγορία"] in cats else 0
                            edit_cat = st.selectbox("Κατηγορία", cats, index=cat_index, key=f"edit_cat_{idx}")
                            edit_amount = st.number_input("Ποσό (€)", value=float(row["Ποσό"]), min_value=0.0, format="%.2f", key=f"edit_amt_{idx}")

                            if st.button("Ενημέρωση", key=f"save_edit_{idx}"):
                                row_to_edit = int(idx) + 2
                                rec_state = row["Επαναλαμβανόμενο"] if "Επαναλαμβανόμενο" in row else "Όχι"
                                worksheet.update(f"A{row_to_edit}:G{row_to_edit}", [[str(edit_date), edit_desc, edit_type, edit_cat, edit_amount, rec_state, current_user]])
                                st.cache_data.clear()
                                st.rerun()
                    with a2:
                        with st.popover("🗑️"):
                            st.write("Διαγραφή;")
                            if st.button("Ναι!", key=f"confirm_del_{idx}", type="primary"):
                                row_to_delete = int(idx) + 2
                                worksheet.delete_rows(row_to_delete)
                                st.cache_data.clear()
                                st.rerun()
                    with a3:
                        st.markdown(f"<div style='text-align: right; font-weight: bold; font-size: 13px; color: {amt_color};'>{row['Ποσό']:.2f}€</div>", unsafe_allow_html=True)
                
                st.markdown("<hr style='margin: 3px 0; border-color: #222222;'>", unsafe_allow_html=True)

            # PAGINATION CONTROLS
            p_col1, p_col2, p_col3 = st.columns([1, 2, 1])
            with p_col1:
                if current_page > 1:
                    if st.button("⬅️ Προηγούμενη", key="prev_page"):
                        st.session_state["history_page"] -= 1
                        st.rerun()
            with p_col2:
                st.markdown(f"<div style='text-align: center; color: #888888; font-size: 13px;'>Σελίδα <b>{current_page}</b> από <b>{total_pages}</b> ({total_items} εγγραφές)</div>", unsafe_allow_html=True)
            with p_col3:
                if current_page < total_pages:
                    if st.button("Επόμενη ➡️", key="next_page"):
                        st.session_state["history_page"] += 1
                        st.rerun()

        else:
            st.info("Δεν υπάρχουν εγγραφές.")

        st.markdown("---")
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Data')
        excel_data = output.getvalue()

        st.download_button(
            label="📥 Download Excel Report",
            data=excel_data,
            file_name=f"finance_report_{current_user}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # -------------------------------------------------------------------
    # ENOTHTA 2: ΝΕΑ ΚΑΤΑΧΩΡΗΣΗ
    # -------------------------------------------------------------------
    elif "Καταχώρηση" in nav_selected:
        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.subheader("⚡ Smart Quick Log")
            quick_input = st.text_input("Γρήγορη Γραπτή Καταχώρηση (π.χ. 15 σουβλάκια)", key="quick_input_tab")

            if st.button("⚡ Γρήγορη Προσθήκη", key="quick_btn_tab"):
                if quick_input:
                    match = re.search(r"(\d+(?:\.\d+)?)", quick_input)
                    if match:
                        extracted_amount = float(match.group(1))
                        extracted_desc = quick_input.replace(match.group(1), "").strip()
                        desc_lower = extracted_desc.lower()
                        auto_type, auto_cat = "Έξοδο", "Διασκέδαση / Έξοδος"

                        if any(w in desc_lower for w in ["ιδιαίτερα", "μισθός", "φροντιστήριο", "ωδείο", "έσοδο"]):
                            auto_type = "Έσοδο"
                            if "ιδιαίτερα" in desc_lower: auto_cat = "Ιδιαίτερα"
                            elif "φροντιστήριο" in desc_lower: auto_cat = "Φροντιστήριο"
                            else: auto_cat = "Άλλα Έσοδα / Έκτακτα"
                        else:
                            if any(w in desc_lower for w in ["super", "market", "φαγητό", "μάρκετ"]): auto_cat = "Super Market"
                            elif any(w in desc_lower for w in ["βενζίνη", "κάρτα", "διόδια", "diesel"]): auto_cat = "Μετακινήσεις"
                            elif any(w in desc_lower for w in ["δεη", "νερό", "ενοίκιο", "cosmote"]): auto_cat = "Πάγια / Λογαριασμοί"

                        today_str = str(datetime.date.today())
                        worksheet.append_row([today_str, extracted_desc if extracted_desc else "Γρήγορη Καταχώρηση", auto_type, auto_cat, extracted_amount, "Όχι", current_user], value_input_option="USER_ENTERED")
                        st.cache_data.clear()
                        st.success(f"Προστέθηκε: {extracted_desc} - {extracted_amount}€")
                        st.rerun()

            st.markdown("---")
            st.subheader("➕ Χειροκίνητη Καταχώρηση")
            entry_type = st.radio("Τύπος", ["Έσοδο", "Έξοδο"], horizontal=True, key="manual_type")
            date = st.date_input("Ημερομηνία", key="manual_date")
            description = st.text_input("Περιγραφή", key="manual_desc")
            cats = INCOME_CATEGORIES if entry_type == "Έσοδο" else EXPENSE_CATEGORIES
            category = st.selectbox("Κατηγορία", cats, key="manual_cat")
            amount = st.number_input("Ποσό (€)", value=0.0, min_value=0.0, format="%.2f", key="manual_amt")
            is_recurring = st.checkbox("🔄 Επαναλαμβανόμενο (Μηνιαίο)", key="manual_rec")

            if st.button("Αποθήκευση Εγγραφής", key="manual_save"):
                rec_val = "Ναι" if is_recurring else "Όχι"
                worksheet.append_row([str(date), description, entry_type, category, float(amount), rec_val, current_user], value_input_option="USER_ENTERED")
                st.cache_data.clear()
                st.success("Η εγγραφή αποθηκεύτηκε επιτυχώς!")
                st.rerun()

        with col_right:
            st.subheader("📸 Receipt Scanner (OCR)")
            uploaded_receipt = st.file_uploader("Ανέβασμα Απόδειξης (JPG/PNG)", type=["jpg", "png", "jpeg"], key="ocr_file")

            scanned_amount = 0.0
            scanned_desc = ""
            scanned_category = "Super Market"

            if uploaded_receipt is not None:
                st.image(uploaded_receipt, caption="Απόδειξη", use_container_width=True)
                try:
                    img = Image.open(uploaded_receipt).convert('L')
                    import pytesseract
                    extracted_text = pytesseract.image_to_string(img, lang='ell+eng', config='--psm 6')
                    amounts = re.findall(r'\b\d+[\.,]\d{2}\b', extracted_text)
                    if amounts:
                        clean_amounts = [float(a.replace(',', '.')) for a in amounts if float(a.replace(',', '.')) < 2000]
                        if clean_amounts: scanned_amount = max(clean_amounts)
                    text_lower = extracted_text.lower()
                    if any(w in text_lower for w in ["μασούτης", "σκλαβενίτης", "lidl", "αβ", "super"]):
                        scanned_desc, scanned_category = "Super Market", "Super Market"
                    elif any(w in text_lower for w in ["bp", "shell", "eko", "diesel", "βενζίνη"]):
                        scanned_desc, scanned_category = "Πρατήριο Καυσίμων", "Μετακινήσεις"
                    else: scanned_desc = "Αγορά από Απόδειξη"
                except Exception:
                    scanned_desc = "Νέα Απόδειξη"

                st.markdown("**🔍 Επιβεβαίωση Σάρωσης:**")
                scanned_amount = st.number_input("Ποσό (€)", value=float(scanned_amount), step=0.10, key="scan_amt_tab")
                scanned_desc = st.text_input("Περιγραφή", value=scanned_desc if scanned_desc else "Απόδειξη", key="scan_desc_tab")
                scanned_category = st.selectbox("Κατηγορία", EXPENSE_CATEGORIES, index=EXPENSE_CATEGORIES.index(scanned_category) if scanned_category in EXPENSE_CATEGORIES else 0, key="scan_cat_tab")

                if st.button("📥 Άμεση Καταχώρηση Απόδειξης", key="scan_save_btn"):
                    today_str = str(datetime.date.today())
                    worksheet.append_row([today_str, scanned_desc, "Έξοδο", scanned_category, scanned_amount, "Όχι", current_user], value_input_option="USER_ENTERED")
                    st.cache_data.clear()
                    st.success("🎉 Η απόδειξη καταχωρήθηκε επιτυχώς!")
                    st.rerun()

    # -------------------------------------------------------------------
    # ENOTHTA 3: ΡΥΘΜΙΣΕΙΣ & ΠΡΟΦΙΛ
    # -------------------------------------------------------------------
    elif "Προφίλ" in nav_selected:
        st.subheader("🎨 Εμφάνιση")
        new_theme = st.radio("Θέμα Εμφάνισης", ["Dark Mode 🌙", "Light Mode ☀️"], index=0 if theme == "Dark Mode 🌙" else 1, horizontal=True)
        if new_theme != theme:
            st.session_state["theme"] = new_theme
            st.rerun()

        st.markdown("---")
        st.subheader("💰 Αρχικό Ταμείο")
        new_start_bal = st.number_input("Ορισμός Αρχικού Υπολοίπου (€)", value=float(STARTING_BALANCE), step=50.00, key="set_start_bal")
        if st.button("Ενημέρωση Αρχικού Ταμείου"):
            try:
                users_data = users_sheet.get_all_records()
                user_row_idx = None
                for idx, u in enumerate(users_data):
                    if str(u.get("Username", "")).strip().lower() == current_user.lower():
                        user_row_idx = idx + 2
                        break
                if user_row_idx:
                    users_sheet.update_cell(user_row_idx, 5, new_start_bal)
                    st.session_state["starting_balance"] = new_start_bal
                    st.success("✅ Το Αρχικό Ταμείο ενημερώθηκε επιτυχώς!")
                    st.rerun()
            except Exception:
                st.error("❌ Σφάλμα κατά την ενημέρωση.")

        st.markdown("---")
        st.subheader("💾 Backup / Restore Δεδομένων (JSON)")
        col_j1, col_p2 = st.columns(2)
        with col_j1:
            if not df.empty:
                json_str = df.to_json(orient="records", force_ascii=False)
                st.download_button(
                    label="📥 Download JSON Backup",
                    data=json_str,
                    file_name=f"finance_backup_{current_user}.json",
                    mime="application/json"
                )
        with col_p2:
            uploaded_json = st.file_uploader("Εισαγωγή JSON Backup", type=["json"], key="json_restore")
            if uploaded_json is not None:
                if st.button("🔄 Επαναφορά Δεδομένων"):
                    try:
                        restore_data = json.load(uploaded_json)
                        for item in restore_data:
                            worksheet.append_row([
                                str(item.get("Ημερομηνία")),
                                str(item.get("Περιγραφή", "")),
                                str(item.get("Τύπος")),
                                str(item.get("Κατηγορία")),
                                float(item.get("Ποσό", 0.0)),
                                str(item.get("Επαναλαμβανόμενο", "Όχι")),
                                current_user
                            ], value_input_option="USER_ENTERED")
                        st.cache_data.clear()
                        st.success("🎉 Τα δεδομένα επαναφέρθηκαν επιτυχώς!")
                        st.rerun()
                    except Exception:
                        st.error("❌ Σφάλμα κατά την ανάγνωση του αρχείου JSON.")

        st.markdown("---")
        st.subheader("🔑 Ασφάλεια Λογαριασμού")
        col_p1, col_p2 = st.columns([1, 2])
        with col_p1:
            email_val = st.text_input("Email Ειδοποιήσεων", value=user_email, key="p_email")
            curr_pass = st.text_input("Τρέχων Κωδικός", type="password", key="p_curr")
            new_pass = st.text_input("Νέος Κωδικός", type="password", key="p_new")
            conf_pass = st.text_input("Επιβεβαίωση Νέου Κωδικού", type="password", key="p_conf")
            
            if st.button("Ενημέρωση Προφίλ", key="p_btn"):
                try:
                    users_data = users_sheet.get_all_records()
                    user_row_idx = None
                    for idx, u in enumerate(users_data):
                        if str(u.get("Username", "")).strip().lower() == current_user.lower():
                            user_row_idx = idx + 2
                            break
                    if user_row_idx:
                        if email_val != user_email:
                            users_sheet.update_cell(user_row_idx, 4, email_val)
                            st.session_state["user_email"] = email_val
                            st.success("✅ Το email ενημερώθηκε!")
                        
                        if new_pass:
                            if not check_hash(curr_pass, str(users_data[user_row_idx-2].get("PasswordHash"))):
                                st.error("❌ Ο τρέχων κωδικός είναι λανθασμένος.")
                            elif new_pass != conf_pass:
                                st.error("❌ Οι νέοι κωδικοί δεν ταιριάζουν!")
                            elif len(new_pass) < 4:
                                st.warning("⚠️ Ο νέος κωδικός πρέπει να έχει τουλάχιστον 4 χαρακτήρες.")
                            else:
                                new_hash = make_hash(new_pass)
                                users_sheet.update_cell(user_row_idx, 2, new_hash)
                                st.success("✅ Ο κωδικός άλλαξε επιτυχώς!")
                except Exception:
                    st.error("❌ Σφάλμα κατά την ενημέρωση.")

    # --- FOOTER ---
    st.markdown("<br><hr>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="text-align: center; color: #888888; font-size: 12px; margin-bottom: 20px;">
            💻 <b>FinancePRO</b> | Designed & Developed by <b>Σπύρος Βοϊκόπουλος</b> <br>
            ⚡ Powered by Streamlit & Google Sheets API
        </div>
        """,
        unsafe_allow_html=True
    )

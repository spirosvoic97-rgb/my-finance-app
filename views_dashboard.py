import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import datetime
import calendar
from io import BytesIO
from config import INCOME_CATEGORIES, EXPENSE_CATEGORIES

def render_dashboard(df, worksheet, current_user, STARTING_BALANCE, selected_year, selected_month, search_query, plotly_template, chart_bg, chart_font_color, chart_grid_color, card_bg):
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

    now = datetime.date.today()
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    days_remaining = (days_in_month - now.day) + 1
    safe_to_spend_daily = (final_balance / days_remaining) if final_balance > 0 and days_remaining > 0 else 0.0
    
    passed_days = now.day
    daily_burn_rate = (total_expenses / passed_days) if passed_days > 0 else 0.0
    savings_rate = ((total_income - total_expenses) / total_income * 100) if total_income > 0 else 0.0

    st.markdown(
        f"""
        <div style="background-color: {card_bg}; padding: 18px 12px; border-radius: 12px; margin-bottom: 12px; text-align: center; border: 1px solid #333333;">
            <div style="font-size: 13px; color: #A0A0A0; font-weight: 500;">Συνολικό Υπόλοιπο</div>
            <div style="font-size: 38px; font-weight: bold; margin: 4px 0; color: {chart_font_color};">{final_balance:,.2f} €</div>
            <div style="font-size: 12px; margin-top: 8px; display: flex; justify-content: space-around;">
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

    m_col1, m_col2 = st.columns(2)
    with m_col1:
        st.metric(label="📊 Δείκτης Αποταμίευσης", value=f"{savings_rate:.1f}%", help="((Έσοδα - Έξοδα) / Έσοδα) × 100")
    with m_col2:
        st.metric(label="🔥 Ημερήσιο Έξοδο (Burn)", value=f"{daily_burn_rate:.2f} €/ημ", help="Έξοδα Μήνα / Ημέρες που πέρασαν")

    st.markdown("<br>", unsafe_allow_html=True)

    # Waterfall & Pie Charts
    chart_col1, chart_col2 = st.columns([3, 2])
    with chart_col1:
        st.subheader("🌊 Waterfall Analysis")
        if not filtered_df.empty and total_income + total_expenses > 0:
            expense_by_cat = filtered_df[filtered_df["Τύπος"] == "Έξοδο"].groupby("Κατηγορία")["Ποσό"].sum()
            x_list = ["INCOME"] + list(expense_by_cat.index) + ["BALANCE"]
            y_list = [total_income] + list(-expense_by_cat.values) + [0]
            measure_list = ["relative"] + ["relative"] * len(expense_by_cat) + ["total"]

            fig_waterfall = go.Figure(go.Waterfall(
                name="Cashflow", orientation="v", measure=measure_list, x=x_list, textposition="outside",
                text=[f"{val:.2f}" if val != 0 else f"{net_month:.2f}" for val in y_list[:-1]] + [f"{net_month:.2f}"],
                textfont=dict(color=chart_font_color, size=11), y=y_list,
                connector={"line": {"color": "rgb(63, 63, 63)"}}, decreasing={"marker": {"color": "#EF553B"}},
                increasing={"marker": {"color": "#636EFA"}}, totals={"marker": {"color": "#7F7F7F"}}
            ))
            fig_waterfall.update_layout(showlegend=False, template=plotly_template, paper_bgcolor=chart_bg, plot_bgcolor=chart_bg, font=dict(color=chart_font_color), height=300)
            st.plotly_chart(fig_waterfall, use_container_width=True, config={'scrollZoom': False, 'displayModeBar': False})
        else:
            st.info("Δεν υπάρχουν δεδομένα.")

    with chart_col2:
        st.subheader("🍕 Κατανομή Εξόδων")
        if not filtered_df.empty and total_expenses > 0:
            exp_df = filtered_df[filtered_df["Τύπος"] == "Έξοδο"]
            fig_pie = px.pie(exp_df, values="Ποσό", names="Κατηγορία", hole=0.4, template=plotly_template)
            fig_pie.update_layout(height=300, paper_bgcolor=chart_bg, plot_bgcolor=chart_bg, font=dict(color=chart_font_color))
            st.plotly_chart(fig_pie, use_container_width=True, config={'scrollZoom': False, 'displayModeBar': False})
        else:
            st.info("Δεν υπάρχουν έξοδα.")

    st.markdown("---")
    st.subheader("📋 Ιστορικό Εγγραφών")
    if not filtered_df.empty:
        display_hist = filtered_df.sort_values(by="Ημερομηνία", ascending=False).copy()
        display_hist["Ποσό (€)"] = display_hist.apply(lambda r: f"{'+' if r['Τύπος']=='Έσοδο' else '-'}{r['Ποσό']:.2f} €", axis=1)
        table_df = display_hist[["Ημερομηνία", "Κατηγορία", "Περιγραφή", "Ποσό (€)"]].reset_index(drop=True)
        
        st.dataframe(table_df, use_container_width=True, height=260, hide_index=True)
        
        with st.expander("✏️ Επεξεργασία / Διαγραφή Εγγραφής"):
            selected_row_idx = st.selectbox("Επιλογή Εγγραφής:", options=range(len(table_df)), format_func=lambda i: f"{table_df.iloc[i]['Ημερομηνία']} - {table_df.iloc[i]['Κατηγορία']} ({table_df.iloc[i]['Ποσό (€)']})")
            if selected_row_idx is not None:
                row_data = display_hist.iloc[selected_row_idx]
                e_col1, e_col2 = st.columns(2)
                with e_col1:
                    edit_date = st.date_input("Ημερομηνία", pd.to_datetime(row_data["Ημερομηνία"]))
                    edit_type = st.radio("Τύπος", ["Έσοδο", "Έξοδο"], index=0 if row_data["Τύπος"] == "Έσοδο" else 1)
                    cats = INCOME_CATEGORIES if edit_type == "Έσοδο" else EXPENSE_CATEGORIES
                    edit_cat = st.selectbox("Κατηγορία", cats, index=cats.index(row_data["Κατηγορία"]) if row_data["Κατηγορία"] in cats else 0)
                with e_col2:
                    edit_desc = st.text_input("Περιγραφή", value=row_data["Περιγραφή"])
                    edit_amount = st.number_input("Ποσό (€)", value=float(row_data["Ποσό"]), min_value=0.0, format="%.2f")
                    btn_c1, btn_c2 = st.columns(2)
                    with btn_c1:
                        if st.button("💾 Ενημέρωση"):
                            row_to_edit = int(row_data.name) + 2
                            worksheet.update(f"A{row_to_edit}:G{row_to_edit}", [[str(edit_date), edit_desc, edit_type, edit_cat, edit_amount, "Όχι", current_user]])
                            st.cache_data.clear()
                            st.rerun()
                    with btn_c2:
                        if st.button("🗑️ Διαγραφή", type="primary"):
                            row_to_delete = int(row_data.name) + 2
                            worksheet.delete_rows(row_to_delete)
                            st.cache_data.clear()
                            st.rerun()

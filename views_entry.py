import streamlit as st
import datetime
import json
import pandas as pd
from io import BytesIO
from PIL import Image, ImageOps
from google import genai
from pydantic import BaseModel, Field
from typing import List, Literal
from config import INCOME_CATEGORIES, EXPENSE_CATEGORIES

class ItemLine(BaseModel):
    item_name: str = Field(description="Όνομα προϊόντος/υπηρεσίας")
    price: float = Field(description="Τιμή μονάδας ή συνόλου γραμμής σε ευρώ")

class ReceiptSchema(BaseModel):
    amount: float = Field(description="Το τελικό συνολικό ποσό πληρωμής σε ευρώ (ΣΥΝΟΛΟ/TOTAL)")
    description: str = Field(description="Το όνομα της επιχείρησης/καταστήματος")
    category: Literal[
        "Super Market", "Αποταμίευση", "Διασκέδαση / Έξοδος", 
        "Έκτακτα / Δώρα / Ταξίδια", "Μετακινήσεις", "Πάγια / Λογαριασμοί", 
        "Προσωπικά / Χόμπι", "Επαγγελματικά Έξοδα"
    ]
    items: List[ItemLine] = Field(default=[], description="Λίστα με τα μεμονωμένα προϊόντα/υπηρεσίες της απόδειξης")

class AutoCategorySchema(BaseModel):
    category: Literal[
        "Super Market", "Αποταμίευση", "Διασκέδαση / Έξοδος", 
        "Έκτακτα / Δώρα / Ταξίδια", "Μετακινήσεις", "Πάγια / Λογαριασμοί", 
        "Προσωπικά / Χόμπι", "Επαγγελματικά Έξοδα"
    ]

def render_entry(worksheet, current_user):
    col_left, col_right = st.columns([1, 1])

    # --- LEFT COLUMN: MANUAL ENTRY ---
    with col_left:
        st.subheader("➕ Χειροκίνητη Καταχώρηση")
        entry_type = st.radio("Τύπος", ["Έσοδο", "Έξοδο"], horizontal=True, key="manual_type")
        date = st.date_input("Ημερομηνία", key="manual_date")
        description = st.text_input("Περιγραφή", key="manual_desc", placeholder="π.χ. Αλλαγή λαδιών Peugeot")

        cats = INCOME_CATEGORIES if entry_type == "Έσοδο" else EXPENSE_CATEGORIES
        
        suggested_idx = 0
        if description and entry_type == "Έξοδο" and "GEMINI_API_KEY" in st.secrets:
            if st.button("🪄 AI Προτεινόμενη Κατηγορία", key="ai_suggest_cat"):
                try:
                    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                    res = client.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=f"Κατηγοριοποίησε τη δαπάνη: '{description}'",
                        config={
                            'response_mime_type': 'application/json',
                            'response_schema': AutoCategorySchema,
                        }
                    )
                    suggested_cat = json.loads(res.text).get("category")
                    if suggested_cat in cats:
                        suggested_idx = cats.index(suggested_cat)
                        st.session_state["selected_cat_idx"] = suggested_idx
                        st.success(f"🤖 Προτάθηκε: {suggested_cat}")
                except Exception:
                    pass

        current_idx = st.session_state.get("selected_cat_idx", 0)
        if current_idx >= len(cats): current_idx = 0

        category = st.selectbox("Κατηγορία", cats, index=current_idx, key="manual_cat")
        amount = st.number_input("Ποσό (€)", value=0.0, min_value=0.0, format="%.2f", key="manual_amt")

        if st.button("Αποθήκευση Εγγραφής", key="manual_save"):
            worksheet.append_row([str(date), description, entry_type, category, float(amount), "Όχι", current_user], value_input_option="USER_ENTERED")
            st.cache_data.clear()
            if "selected_cat_idx" in st.session_state: del st.session_state["selected_cat_idx"]
            st.success("Η εγγραφή αποθηκεύτηκε επιτυχώς!")
            st.rerun()

    # --- RIGHT COLUMN: RECEIPT SCANNER ---
    with col_right:
        st.subheader("📸 Receipt Scanner (AI Vision)")

        if "uploader_key" not in st.session_state:
            st.session_state["uploader_key"] = 0

        uploaded_receipt = st.file_uploader("Ανέβασμα Απόδειξης (JPG/PNG)", type=["jpg", "png", "jpeg"], key=f"ocr_file_{st.session_state['uploader_key']}")

        scanned_amount, scanned_desc, scanned_category = 0.0, "Απόδειξη", "Super Market"
        extracted_items = []

        if uploaded_receipt is not None:
            img = Image.open(uploaded_receipt)
            try: img = ImageOps.exif_transpose(img)
            except Exception: pass

            st.image(img, caption="Απόδειξη", use_container_width=True)

            img_byte_arr = BytesIO()
            img.save(img_byte_arr, format='JPEG')
            img_bytes = img_byte_arr.getvalue()

            if "GEMINI_API_KEY" in st.secrets and str(st.secrets["GEMINI_API_KEY"]).strip() != "":
                try:
                    with st.spinner("🤖 Η AI αναλύει την απόδειξη..."):
                        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                        prompt = "Ανάλυσε την απόδειξη. Εξάγαγε το συνολικό ποσό, το κατάστημα, την κατηγορία και τη λίστα προϊόντων."
                        
                        response = client.models.generate_content(
                            model='gemini-3.6-flash',
                            contents=[prompt, genai.types.Part.from_bytes(data=img_bytes, mime_type='image/jpeg')],
                            config={
                                'response_mime_type': 'application/json',
                                'response_schema': ReceiptSchema,
                            }
                        )
                        
                        parsed = json.loads(response.text)
                        scanned_amount = float(parsed.get("amount", 0.0))
                        scanned_desc = str(parsed.get("description", "Απόδειξη"))
                        scanned_category = str(parsed.get("category", "Super Market"))
                        extracted_items = parsed.get("items", [])

                        st.success(f"✅ Εντοπίστηκε: {scanned_desc} - {scanned_amount:.2f}€")
                except Exception as e:
                    st.error(f"⚠️ Σφάλμα AI: {e}")

            st.markdown("**🔍 Επιβεβαίωση Σάρωσης:**")
            scanned_amount = st.number_input("Ποσό (€)", value=float(scanned_amount), step=0.10, key="scan_amt_tab")
            scanned_desc = st.text_input("Περιγραφή", value=scanned_desc, key="scan_desc_tab")
            scanned_category = st.selectbox("Κατηγορία", EXPENSE_CATEGORIES, index=EXPENSE_CATEGORIES.index(scanned_category) if scanned_category in EXPENSE_CATEGORIES else 0, key="scan_cat_tab")

            if extracted_items:
                with st.expander("🛒 Αναλυτικά Προϊόντα Απόδειξης"):
                    for item in extracted_items:
                        st.write(f"• **{item.get('item_name')}**: {item.get('price'):.2f}€")

            if st.button("📥 Άμεση Καταχώρηση Απόδειξης", key="scan_save_btn"):
                today_str = str(datetime.date.today())
                worksheet.append_row([today_str, scanned_desc, "Έξοδο", scanned_category, scanned_amount, "Όχι", current_user], value_input_option="USER_ENTERED")
                st.cache_data.clear()
                st.session_state["uploader_key"] += 1
                st.success("🎉 Η απόδειξη καταχωρήθηκε επιτυχώς!")
                st.rerun()

    # --- BOTTOM SECTION: EDIT & DELETE RECENT ENTRIES ---
    st.markdown("---")
    st.subheader("🛠️ Διαχείριση & Διόρθωση Εγγραφών")

    try:
        all_vals = worksheet.get_all_values()
    except Exception:
        all_vals = []

    if len(all_vals) > 1:
        headers = [str(h).strip() for h in all_vals[0]]
        df = pd.DataFrame(all_vals[1:], columns=headers)
        
        # Φιλτράρισμα μόνο για τις εγγραφές του τρέχοντος χρήστη
        if "Username" in df.columns:
            user_mask = df["Username"] == current_user
            user_df = df[user_mask].copy()
        else:
            user_df = df.copy()

        if not user_df.empty:
            # Προσθήκη πραγματικού αριθμού γραμμής Sheet (1-based index)
            user_df["Sheet_Row"] = user_df.index + 2

            # Δημιουργία φιλικής περιγραφής για την επιλογή
            user_df["Select_Label"] = user_df.apply(
                lambda r: f"Γραμμή {r['Sheet_Row']}: {r.get('Ημερομηνία', '')} | {r.get('Περιγραφή', '')} | {r.get('Ποσό', '')}€ ({r.get('Τύπος', '')})", axis=1
            )

            selected_label = st.selectbox("Επίλεξε εγγραφή για επεξεργασία ή διαγραφή:", user_df["Select_Label"].tolist(), key="select_edit_row")
            selected_row_data = user_df[user_df["Select_Label"] == selected_label].iloc[0]
            target_row_num = int(selected_row_data["Sheet_Row"])

            col_edit1, col_edit2, col_edit3 = st.columns(3)

            with col_edit1:
                edit_desc = st.text_input("Νέα Περιγραφή", value=str(selected_row_data.get("Περιγραφή", "")), key="edit_desc")
                edit_type = st.selectbox("Νέος Τύπος", ["Έσοδο", "Έξοδο"], index=0 if selected_row_data.get("Τύπος") == "Έσοδο" else 1, key="edit_type")

            with col_edit2:
                edit_amount_val = float(str(selected_row_data.get("Ποσό", 0)).replace(",", ".")) if selected_row_data.get("Ποσό") else 0.0
                edit_amount = st.number_input("Νέο Ποσό (€)", value=edit_amount_val, step=0.10, key="edit_amt")
                
                all_cats = INCOME_CATEGORIES if edit_type == "Έσοδο" else EXPENSE_CATEGORIES
                old_cat = selected_row_data.get("Κατηγορία", "")
                cat_idx = all_cats.index(old_cat) if old_cat in all_cats else 0
                edit_cat = st.selectbox("Νέα Κατηγορία", all_cats, index=cat_idx, key="edit_cat")

            with col_edit3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("💾 Ενημέρωση Εγγραφής", key="btn_update_row"):
                    # Ενημέρωση των κελιών στη συγκεκριμένη γραμμή
                    worksheet.update_cell(target_row_num, 2, edit_desc)
                    worksheet.update_cell(target_row_num, 3, edit_type)
                    worksheet.update_cell(target_row_num, 4, edit_cat)
                    worksheet.update_cell(target_row_num, 5, edit_amount)
                    st.cache_data.clear()
                    st.success("✅ Η εγγραφή ενημερώθηκε επιτυχώς!")
                    st.rerun()

                if st.button("🗑️ Διαγραφή Εγγραφής", key="btn_delete_row"):
                    worksheet.delete_rows(target_row_num)
                    st.cache_data.clear()
                    st.success("🗑️ Η εγγραφή διαγράφηκε επιτυχώς!")
                    st.rerun()
        else:
            st.info("Δεν υπάρχουν πρόσφατες εγγραφές για τροποποίηση.")

import streamlit as st
import datetime
import json
import pandas as pd
from io import BytesIO
from PIL import Image, ImageOps
from google import genai
from pydantic import BaseModel, Field
from typing import List
from config import INCOME_CATEGORIES, EXPENSE_CATEGORIES

EXPENSE_CATS_STR = ", ".join([f"'{c}'" for c in EXPENSE_CATEGORIES])

class ItemLine(BaseModel):
    item_name: str = Field(description="Το όνομα του προϊόντος ή της υπηρεσίας.")
    price: float = Field(description="Η τελική τιμή του προϊόντος/υπηρεσίας σε ευρώ.")

class ReceiptSchema(BaseModel):
    amount: float = Field(description="Το ΤΕΛΙΚΟ πληρωτέο ποσό σε ευρώ (ΣΥΝΟΛΟ/TOTAL).")
    description: str = Field(description="Η επωνυμία του καταστήματος/επιχείρησης.")
    category: str = Field(description=f"ΠΡΕΠΕΙ ΑΥΣΤΗΡΑ να είναι ΜΟΝΟ ΜΙΑ από αυτές τις επιλογές: {EXPENSE_CATS_STR}.")
    items: List[ItemLine] = Field(default=[], description="Λίστα με τα μεμονωμένα προϊόντα.")

class AutoCategorySchema(BaseModel):
    category: str = Field(description=f"ΠΡΕΠΕΙ ΑΥΣΤΗΡΑ να είναι ΜΟΝΟ ΜΙΑ από αυτές τις επιλογές: {EXPENSE_CATS_STR}.")

def process_image_for_api(img, max_size=(1024, 1024)):
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.thumbnail(max_size, Image.Resampling.LANCZOS)
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='JPEG', quality=85)
    return img_byte_arr.getvalue()

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
                        contents=f"Ανάλυσε τη δαπάνη: '{description}'. Επίλεξε την πιο ταιριαστή κατηγορία.",
                        config={
                            'response_mime_type': 'application/json',
                            'response_schema': AutoCategorySchema,
                            'temperature': 0.1
                        }
                    )
                    suggested_cat = json.loads(res.text).get("category")
                    if suggested_cat in cats:
                        suggested_idx = cats.index(suggested_cat)
                        st.session_state["selected_cat_idx"] = suggested_idx
                        st.success(f"🤖 Προτάθηκε: {suggested_cat}")
                    else:
                        st.warning("Το AI επέστρεψε άγνωστη κατηγορία.")
                except Exception:
                    st.error("⚠️ Αποτυχία σύνδεσης με AI.")

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
            
        if "scan_results" not in st.session_state:
            st.session_state["scan_results"] = None

        uploaded_receipt = st.file_uploader("Ανέβασμα Απόδειξης (JPG/PNG)", type=["jpg", "png", "jpeg"], key=f"ocr_file_{st.session_state['uploader_key']}")

        if uploaded_receipt is not None:
            if "last_file_name" not in st.session_state or st.session_state["last_file_name"] != uploaded_receipt.name:
                st.session_state["scan_results"] = None
                st.session_state["last_file_name"] = uploaded_receipt.name

            img = Image.open(uploaded_receipt)
            try: img = ImageOps.exif_transpose(img)
            except Exception: pass

            st.image(img, caption="Απόδειξη προς Ανάλυση", use_container_width=True)
            img_bytes = process_image_for_api(img)

            if st.button("🧠 Έναρξη Ανάλυσης AI", key="btn_start_ai"):
                if "GEMINI_API_KEY" in st.secrets and str(st.secrets["GEMINI_API_KEY"]).strip() != "":
                    try:
                        with st.spinner("🤖 Η AI αναλύει την απόδειξη... (παρακαλώ περιμένετε)"):
                            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                            
                            prompt = (
                                "Διάβασε την απόδειξη."
                                "1. Βρες το τελικό πληρωτέο ποσό."
                                "2. Βρες την επωνυμία της επιχείρησης."
                                "3. Επίλεξε ΑΥΣΤΗΡΑ μία από τις κατηγορίες που σου δόθηκαν στο schema."
                                "4. Κατάγραψε τα προϊόντα."
                            )
                            
                            response = client.models.generate_content(
                                model='gemini-3.6-flash',
                                contents=[prompt, genai.types.Part.from_bytes(data=img_bytes, mime_type='image/jpeg')],
                                config={
                                    'response_mime_type': 'application/json',
                                    'response_schema': ReceiptSchema,
                                    'temperature': 0.1
                                }
                            )
                            
                            parsed = json.loads(response.text)
                            st.session_state["scan_results"] = parsed
                            st.success("✅ Ανάλυση Ολοκληρώθηκε!")
                    except Exception as e:
                        st.error(f"⚠️ Σφάλμα AI κατά την ανάλυση: {e}")

            if st.session_state["scan_results"] is not None:
                res = st.session_state["scan_results"]
                
                st.markdown("---")
                st.markdown("**🔍 Επιβεβαίωση Δεδομένων:**")
                scanned_amount = st.number_input("Ποσό (€)", value=float(res.get("amount", 0.0)), step=0.10, key="scan_amt_tab")
                scanned_desc = st.text_input("Περιγραφή", value=str(res.get("description", "Άγνωστο Κατάστημα")), key="scan_desc_tab")
                
                temp_cat = str(res.get("category", EXPENSE_CATEGORIES[0]))
                safe_cat = temp_cat if temp_cat in EXPENSE_CATEGORIES else EXPENSE_CATEGORIES[0]
                scanned_category = st.selectbox("Κατηγορία", EXPENSE_CATEGORIES, index=EXPENSE_CATEGORIES.index(safe_cat), key="scan_cat_tab")

                extracted_items = res.get("items", [])
                if extracted_items:
                    with st.expander("🛒 Αναλυτικά Προϊόντα Απόδειξης"):
                        for item in extracted_items:
                            st.write(f"• **{item.get('item_name')}**: {item.get('price'):.2f}€")

                if st.button("📥 Άμεση Καταχώρηση Απόδειξης", key="scan_save_btn"):
                    today_str = str(datetime.date.today())
                    worksheet.append_row([today_str, scanned_desc, "Έξοδο", scanned_category, scanned_amount, "Όχι", current_user], value_input_option="USER_ENTERED")
                    
                    st.cache_data.clear()
                    st.session_state["uploader_key"] += 1
                    st.session_state["scan_results"] = None 
                    
                    st.success("🎉 Η απόδειξη καταχωρήθηκε επιτυχώς!")
                    st.rerun()

    # --- BOTTOM SECTION: EDIT & DELETE WITH SORTING FILTERS ---
    st.markdown("---")
    st.subheader("🛠️ Διαχείριση & Διόρθωση Εγγραφών")

    try:
        all_vals = worksheet.get_all_values()
    except Exception:
        all_vals = []

    if len(all_vals) > 1:
        headers = [str(h).strip() for h in all_vals[0]]
        df = pd.DataFrame(all_vals[1:], columns=headers)
        
        if "Username" in df.columns:
            user_mask = df["Username"] == current_user
            user_df = df[user_mask].copy()
        else:
            user_df = df.copy()

        if not user_df.empty:
            user_df["Sheet_Row"] = user_df.index + 2

            # Προετοιμασία στηλών για ταξινόμηση
            user_df["Numeric_Amount"] = pd.to_numeric(user_df["Ποσό"].astype(str).str.replace(",", "."), errors="coerce").fillna(0.0)
            user_df["Parsed_Date"] = pd.to_datetime(user_df["Ημερομηνία"], errors="coerce")

            # --- ΧΕΙΡΙΣΤΗΡΙΟ ΤΑΞΙΝΟΜΗΣΗΣ ---
            col_sort1, col_sort2 = st.columns([2, 1])
            with col_sort1:
                sort_option = st.selectbox(
                    "📊 Ταξινόμηση εγγραφών κατά:",
                    [
                        "Ημερομηνία (Φθίνουσα - Νεότερες πρώτα)",
                        "Ημερομηνία (Αύξουσα - Παλαιότερες πρώτα)",
                        "Ποσό (Φθίνουσα - Μεγαλύτερα πρώτα)",
                        "Ποσό (Αύξουσα - Μικρότερα πρώτα)"
                    ],
                    key="sort_option_select"
                )

            # Εφαρμογή Ταξινόμησης
            if sort_option == "Ημερομηνία (Φθίνουσα - Νεότερες πρώτα)":
                user_df = user_df.sort_values(by="Parsed_Date", ascending=False)
            elif sort_option == "Ημερομηνία (Αύξουσα - Παλαιότερες πρώτα)":
                user_df = user_df.sort_values(by="Parsed_Date", ascending=True)
            elif sort_option == "Ποσό (Φθίνουσα - Μεγαλύτερα πρώτα)":
                user_df = user_df.sort_values(by="Numeric_Amount", ascending=False)
            elif sort_option == "Ποσό (Αύξουσα - Μικρότερα πρώτα)":
                user_df = user_df.sort_values(by="Numeric_Amount", ascending=True)

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

import streamlit as st
import datetime
import json
from io import BytesIO
from PIL import Image, ImageOps
from google import genai
from pydantic import BaseModel, Field
from typing import List, Literal
from config import INCOME_CATEGORIES, EXPENSE_CATEGORIES

# --- PYDANTIC SCHEMAS FOR STRICT AI OUTPUT ---
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

    # --- LEFT COLUMN: MANUAL ENTRY WITH SMART AUTO-CATEGORIZATION ---
    with col_left:
        st.subheader("➕ Χειροκίνητη Καταχώρηση")
        entry_type = st.radio("Τύπος", ["Έσοδο", "Έξοδο"], horizontal=True, key="manual_type")
        date = st.date_input("Ημερομηνία", key="manual_date")
        description = st.text_input("Περιγραφή", key="manual_desc", placeholder="π.χ. Αλλαγή λαδιών Peugeot")

        cats = INCOME_CATEGORIES if entry_type == "Έσοδο" else EXPENSE_CATEGORIES
        
        # AI Auto-Categorization Trigger
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

    # --- RIGHT COLUMN: ADVANCED MULTI-ITEM AI OCR SCANNER ---
    with col_right:
        st.subheader("📸 Receipt Scanner (Advanced AI Vision)")

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
                    with st.spinner("🤖 Η AI αναλύει την απόδειξη & τα προϊόντα..."):
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
            else:
                st.warning("⚠️ Το GEMINI_API_KEY δεν βρέθηκε στα Secrets!")

            st.markdown("**🔍 Επιβεβαίωση Σάρωσης:**")
            scanned_amount = st.number_input("Ποσό (€)", value=float(scanned_amount), step=0.10, key="scan_amt_tab")
            scanned_desc = st.text_input("Περιγραφή", value=scanned_desc, key="scan_desc_tab")
            scanned_category = st.selectbox("Κατηγορία", EXPENSE_CATEGORIES, index=EXPENSE_CATEGORIES.index(scanned_category) if scanned_category in EXPENSE_CATEGORIES else 0, key="scan_cat_tab")

            # Εμφάνιση αναλυτικής λίστας προϊόντων αν υπάρχουν
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

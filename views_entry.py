import streamlit as st
import datetime
import json
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

def render_entry(worksheet, current_user, t=None):
    col_left, col_right = st.columns([1, 1])

    # --- LEFT COLUMN: MANUAL ENTRY ---
    with col_left:
        st.subheader("➕ Χειροκίνητη Καταχώρηση")
        entry_type = st.radio("Τύπος", ["Έσοδο", "Έξοδο"], horizontal=True, key="manual_type")
        date = st.date_input("Ημερομηνία", key="manual_date")
        
        # Πεδία με Session State για αυτόματο μηδενισμό μετά την αποθήκευση
        description = st.text_input("Περιγραφή", key="manual_desc_input", placeholder="π.χ. Αλλαγή λαδιών")

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
                except Exception:
                    st.error("⚠️ Αποτυχία σύνδεσης με AI.")

        current_idx = st.session_state.get("selected_cat_idx", 0)
        if current_idx >= len(cats): current_idx = 0

        category = st.selectbox("Κατηγορία", cats, index=current_idx, key="manual_cat")
        amount = st.number_input("Ποσό (€)", min_value=0.0, format="%.2f", key="manual_amt_input")

        if st.button("Αποθήκευση Εγγραφής", key="manual_save"):
            if not description or amount <= 0:
                st.warning("⚠️ Παρακαλώ συμπληρώστε Περιγραφή και Ποσό μεγαλύτερο του 0.")
            else:
                worksheet.append_row([str(date), description, entry_type, category, float(amount), "Όχι", current_user], value_input_option="USER_ENTERED")
                st.cache_data.clear()
                
                # Καθαρισμός πεδίων
                if "selected_cat_idx" in st.session_state: del st.session_state["selected_cat_idx"]
                st.session_state["manual_desc_input"] = ""
                st.session_state["manual_amt_input"] = 0.0
                
                st.success("🎉 Η εγγραφή καταχωρήθηκε επιτυχώς!")
                st.rerun()

    # --- RIGHT COLUMN: RECEIPT SCANNER ---
    with col_right:
        st.subheader("📸 Receipt Scanner (AI Vision)")

        if "uploader_key" not in st.session_state: st.session_state["uploader_key"] = 0
        if "scan_results" not in st.session_state: st.session_state["scan_results"] = None

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
                        with st.spinner("🤖 Η AI αναλύει την απόδειξη..."):
                            client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                            prompt = "Διάβασε την απόδειξη. Βρες ποσό, κατάστημα, κατηγορία, προϊόντα."
                            response = client.models.generate_content(
                                model='gemini-3.6-flash',
                                contents=[prompt, genai.types.Part.from_bytes(data=img_bytes, mime_type='image/jpeg')],
                                config={'response_mime_type': 'application/json', 'response_schema': ReceiptSchema, 'temperature': 0.1}
                            )
                            st.session_state["scan_results"] = json.loads(response.text)
                            st.success("✅ Ανάλυση Ολοκληρώθηκε!")
                    except Exception as e:
                        st.error(f"⚠️ Σφάλμα AI: {e}")

            if st.session_state["scan_results"] is not None:
                res = st.session_state["scan_results"]
                st.markdown("---")
                scanned_amount = st.number_input("Ποσό (€)", value=float(res.get("amount", 0.0)), step=0.10, key="scan_amt_tab")
                scanned_desc = st.text_input("Περιγραφή", value=str(res.get("description", "Άγνωστο Κατάστημα")), key="scan_desc_tab")
                temp_cat = str(res.get("category", EXPENSE_CATEGORIES[0]))
                safe_cat = temp_cat if temp_cat in EXPENSE_CATEGORIES else EXPENSE_CATEGORIES[0]
                scanned_category = st.selectbox("Κατηγορία", EXPENSE_CATEGORIES, index=EXPENSE_CATEGORIES.index(safe_cat), key="scan_cat_tab")

                if st.button("📥 Άμεση Καταχώρηση Απόδειξης", key="scan_save_btn"):
                    today_str = str(datetime.date.today())
                    worksheet.append_row([today_str, scanned_desc, "Έξοδο", scanned_category, scanned_amount, "Όχι", current_user], value_input_option="USER_ENTERED")
                    st.cache_data.clear()
                    st.session_state["uploader_key"] += 1
                    st.session_state["scan_results"] = None 
                    st.success("🎉 Η απόδειξη καταχωρήθηκε επιτυχώς!")
                    st.rerun()

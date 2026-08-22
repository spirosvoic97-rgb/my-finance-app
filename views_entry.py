import streamlit as st
import datetime
import re
import json
from io import BytesIO
from PIL import Image, ImageOps
from google import genai
from config import INCOME_CATEGORIES, EXPENSE_CATEGORIES

def render_entry(worksheet, current_user):
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
                        auto_cat = "Ιδιαίτερα" if "ιδιαίτερα" in desc_lower else "Άλλα Έσοδα / Έκτακτα"
                    else:
                        if any(w in desc_lower for w in ["super", "market", "φαγητό"]): auto_cat = "Super Market"
                        elif any(w in desc_lower for w in ["βενζίνη", "κάρτα"]): auto_cat = "Μετακινήσεις"

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

        if st.button("Αποθήκευση Εγγραφής", key="manual_save"):
            worksheet.append_row([str(date), description, entry_type, category, float(amount), "Όχι", current_user], value_input_option="USER_ENTERED")
            st.cache_data.clear()
            st.success("Η εγγραφή αποθηκεύτηκε επιτυχώς!")
            st.rerun()

    with col_right:
        st.subheader("📸 Receipt Scanner (AI Vision)")
        uploaded_receipt = st.file_uploader("Ανέβασμα Απόδειξης (JPG/PNG)", type=["jpg", "png", "jpeg"], key="ocr_file")

        scanned_amount, scanned_desc, scanned_category = 0.0, "Απόδειξη", "Super Market"

        if uploaded_receipt is not None:
            if "rotation_angle" not in st.session_state: st.session_state["rotation_angle"] = 0
            if st.button("🔄 Περιστροφή 90°"): st.session_state["rotation_angle"] = (st.session_state["rotation_angle"] + 90) % 360

            img = Image.open(uploaded_receipt)
            try: img = ImageOps.exif_transpose(img)
            except Exception: pass

            if st.session_state["rotation_angle"] != 0:
                img = img.rotate(-st.session_state["rotation_angle"], expand=True)

            st.image(img, caption=f"Απόδειξη ({st.session_state['rotation_angle']}°)", use_container_width=True)

            img_byte_arr = BytesIO()
            img.save(img_byte_arr, format='JPEG')
            img_bytes = img_byte_arr.getvalue()

            if "GEMINI_API_KEY" in st.secrets and str(st.secrets["GEMINI_API_KEY"]).strip() != "":
                try:
                    with st.spinner("🤖 Η AI αναλύει την απόδειξη..."):
                        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                        prompt = f"""
                        Ανάλυσε αυτή την εικόνα απόδειξης και επίστρεψε ΜΟΝΟ ένα valid JSON.
                        {{
                            "amount": <float, τελικό ποσό ΣΥΝΟΛΟ/TOTAL σε ευρώ>,
                            "description": <string, όνομα καταστήματος>,
                            "category": <string, μία από: {EXPENSE_CATEGORIES}>
                        }}
                        """
                        response = client.models.generate_content(
                            model='gemini-3.6-flash',
                            contents=[prompt, genai.types.Part.from_bytes(data=img_bytes, mime_type='image/jpeg')]
                        )
                        res_text = response.text.strip()
                        if "```json" in res_text: res_text = res_text.split("```json")[1].split("```")[0].strip()
                        elif "```" in res_text: res_text = res_text.split("```")[1].split("```")[0].strip()
                            
                        parsed = json.loads(res_text)
                        scanned_amount = float(parsed.get("amount", 0.0))
                        scanned_desc = str(parsed.get("description", "Απόδειξη"))
                        cat_candidate = str(parsed.get("category", "Super Market"))
                        scanned_category = cat_candidate if cat_candidate in EXPENSE_CATEGORIES else "Super Market"
                        st.success(f"✅ Εντοπίστηκε: {scanned_desc} - {scanned_amount:.2f}€")
                except Exception as e:
                    st.error(f"⚠️ Σφάλμα AI: {e}")
            else:
                st.warning("⚠️ Το GEMINI_API_KEY δεν βρέθηκε στα Secrets!")

            st.markdown("**🔍 Επιβεβαίωση Σάρωσης:**")
            scanned_amount = st.number_input("Ποσό (€)", value=float(scanned_amount), step=0.10, key="scan_amt_tab")
            scanned_desc = st.text_input("Περιγραφή", value=scanned_desc, key="scan_desc_tab")
            scanned_category = st.selectbox("Κατηγορία", EXPENSE_CATEGORIES, index=EXPENSE_CATEGORIES.index(scanned_category) if scanned_category in EXPENSE_CATEGORIES else 0, key="scan_cat_tab")

            if st.button("📥 Άμεση Καταχώρηση Απόδειξης", key="scan_save_btn"):
                today_str = str(datetime.date.today())
                worksheet.append_row([today_str, scanned_desc, "Έξοδο", scanned_category, scanned_amount, "Όχι", current_user], value_input_option="USER_ENTERED")
                st.cache_data.clear()
                st.success("🎉 Η απόδειξη καταχωρήθηκε επιτυχώς!")
                st.rerun()

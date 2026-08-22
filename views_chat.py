import streamlit as st
import pandas as pd
from google import genai

def render_chat(worksheet, current_user):
    st.subheader("💬 AI Financial Assistant")
    st.caption("Ρώτα την AI οτιδήποτε σχετικό με τα έξοδα, τα έσοδα και τις συνήθειές σου!")

    # Φόρτωση δεδομένων από το Sheet
    records = worksheet.get_all_records()
    df = pd.DataFrame(records)
    
    if df.empty:
        st.info("Δεν υπάρχουν ακόμα εγγραφές για ανάλυση.")
        return

    # Φιλτράρισμα για τον τρέχοντα χρήστη
    if "Username" in df.columns:
        df = df[df["Username"] == current_user]

    # Προετοιμασία σύνοψης δεδομένων για το Prompt
    data_summary = df[["Ημερομηνία", "Περιγραφή", "Τύπος", "Κατηγορία", "Ποσό"]].to_string(index=False)

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    # Εμφάνιση ιστορικού chat
    for message in st.session_state["chat_history"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Εισαγωγή ερώτησης
    user_prompt = st.chat_input("π.χ. Πόσα ξόδεψα σε βενζίνες αυτό το μήνα;")

    if user_prompt:
        st.chat_message("user").markdown(user_prompt)
        st.session_state["chat_history"].append({"role": "user", "content": user_prompt})

        if "GEMINI_API_KEY" in st.secrets:
            try:
                client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                system_prompt = f"""
                Είσαι ένας έμπειρος οικονομικός σύμβουλος. Απάντησε στην ερώτηση του χρήστη με βάση τα παρακάτω οικονομικά δεδομένα του:

                ΔΕΔΟΜΕΝΑ:
                {data_summary}

                Να είσαι σύντομος, ακριβής, φιλικός και να δίνεις χρήσιμες οικονομικές συμβουλές όπου χρειάζεται.
                """
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=[system_prompt, user_prompt]
                )
                ai_reply = response.text
            except Exception as e:
                ai_reply = f"⚠️ Σφάλμα AI: {e}"
        else:
            ai_reply = "⚠️ Το GEMINI_API_KEY δεν βρέθηκε στα Secrets."

        with st.chat_message("assistant"):
            st.markdown(ai_reply)
        st.session_state["chat_history"].append({"role": "assistant", "content": ai_reply})

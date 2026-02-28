import streamlit as st

# --- OLDAL BEÁLLÍTÁSOK ---
st.set_page_config(
    page_title="D&D 5e DM Asszisztens",
    page_icon="🐉",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SESSION STATE INICIALIZÁLÁSA ---
# Itt tároljuk a globális adatokat, amiknek minden oldalon élniük kell
if "party_hp" not in st.session_state:
    st.session_state.party_hp = {}
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [] # Rules lawyer history

st.title("🐉 D&D 5e DM Asszisztens")
st.markdown("""
Üdvözöllek a **Kalandmesteri Pultnál**! 
Válaszd ki a bal oldali menüből, hogy melyik modult szeretnéd használni.

- **🛡️ Dashboard:** Játékosok, Party stash, Pihenők
- **🗺️ VTT Map:** Térképkezelés, Fog of War
- **⚔️ Combat:** Kezdeményezés, Kockák, Harcrend
- **🧠 AI Assistant:** Groq-alapú NJK generátor, Szabálybíró
- **📖 Worldbuilding:** Kapcsolati háló, Jegyzetek
""")

st.info("👈 Kezdd a navigációt a bal oldalsávban!")

import streamlit as st
# Importáljuk a saját segédfüggvényeinket!
from utils.ai_helpers import ask_rules_lawyer, generate_npc

st.set_page_config(page_title="AI Asszisztens", page_icon="🧠", layout="wide")
st.title("🧠 Groq AI Kalandmester Asszisztens")

# Chat történet inicializálása, ha még nem létezik az app.py-ból
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

tab1, tab2, tab3 = st.tabs(["⚖️ Rules Lawyer", "🎭 NJK Generátor", "🏰 Helyszín Leírás"])

# ==========================================
# 1. FÜL: RULES LAWYER
# ==========================================
with tab1:
    st.subheader("D&D 5e Szabálybíró")
    st.caption("Kérdezz bármit az 5e szabályokról! Az AI az SRD alapján válaszol.")

    # Korábbi üzenetek kirajzolása
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Új kérdés bekérése
    if prompt := st.chat_input("Pl.: Hogyan működik a Grapple (birkózás) pontosan?"):
        # UI frissítése a felhasználó kérdésével
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Válasz generálása a utils-ból
        with st.chat_message("assistant"):
            with st.spinner("A szabálykönyvek lapozgatása..."):
                # Itt hívjuk meg a tiszta függvényünket!
                response_text = ask_rules_lawyer(st.session_state.chat_history)
                st.markdown(response_text)
                
            st.session_state.chat_history.append({"role": "assistant", "content": response_text})

# ==========================================
# 2. FÜL: NJK GENERÁTOR
# ==========================================
with tab2:
    st.subheader("Intelligens NJK Generátor")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        npc_race = st.selectbox("Faj", ["Ember", "Tünde (Elf)", "Törp (Dwarf)", "Félszerzet (Halfling)", "Sárkányszülött", "Tiefling", "Egyéb/Véletlen"])
    with col2:
        npc_role = st.selectbox("Szerep/Foglalkozás", ["Kereskedő", "Kocsmáros", "Őr", "Nemes", "Tolvaj", "Varázsló", "Véletlen"])
    with col3:
        npc_vibe = st.text_input("Hangulat / Jellemző", "Barátságos, de kicsit kapzsi")

    if st.button("🎭 NJK Generálása", use_container_width=True):
        with st.spinner("Az istenek formálják a lelket..."):
            # Itt hívjuk meg a tiszta NJK generátor függvényünket!
            npc_result = generate_npc(npc_race, npc_role, npc_vibe)
            
            if "Hiba" in npc_result:
                st.error(npc_result)
            else:
                st.success("NJK Sikeresen Legenerálva!")
                st.markdown(npc_result)

# ==========================================
# 3. FÜL: HELYSZÍN LEÍRÁS
# ==========================================
with tab3:
    st.subheader("Dinamikus Helyszín Leírás (Read-Aloud)")
    st.info("Későbbi fejlesztés: Kulcsszavas helyszíngenerátor.")

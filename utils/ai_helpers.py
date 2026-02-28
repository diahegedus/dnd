import streamlit as st
from groq import Groq
import json

# --- GROQ KLIENS INICIALIZÁLÁSA ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except KeyError:
    st.error("Hiányzik a Groq API kulcs! Kérlek, állítsd be a `.streamlit/secrets.toml` fájlban.")
    st.stop()

# Választható modellek (A LLaMA 3 kiváló és gyors ilyen feladatokra)
MODEL = "llama3-70b-8192" 

st.set_page_config(page_title="AI Asszisztens", page_icon="🧠", layout="wide")
st.title("🧠 Groq AI Kalandmester Asszisztens")

# Fülek létrehozása a funkcióknak
tab1, tab2, tab3 = st.tabs(["⚖️ Rules Lawyer", "🎭 NJK Generátor", "🏰 Helyszín Leírás"])

# ==========================================
# 1. FÜL: RULES LAWYER (Szabálybíró Chat)
# ==========================================
with tab1:
    st.subheader("D&D 5e Szabálybíró")
    st.caption("Kérdezz bármit az 5e szabályokról! Az AI kizárólag a hivatalos SRD (System Reference Document) alapján válaszol.")

    # Chat történet megjelenítése
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Új kérdés bevitele
    if prompt := st.chat_input("Pl.: Hogyan működik a Grapple (birkózás) pontosan?"):
        # Felhasználói üzenet mentése és kiírása
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # AI hívás (System prompttal fókuszálva az 5e-re)
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            
            messages = [
                {"role": "system", "content": "Te egy szakértő Dungeons & Dragons 5e Kalandmester (DM) asszisztens vagy. A feladatod, hogy pontos, tömör válaszokat adj az 5e szabályrendszer alapján. Hivatkozz az SRD-re, ha lehet. Légy objektív, de barátságos. Ha a szabály kétértelmű, javasolj egy igazságos DM döntést (Ruling). Magyarul válaszolj!"}
            ]
            # Hozzáadjuk a korábbi kontextust is
            messages.extend([{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_history])

            try:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    temperature=0.3, # Alacsony temp, hogy ne találjon ki szabályokat
                )
                
                full_response = response.choices[0].message.content
                message_placeholder.markdown(full_response)
                
                # AI válasz mentése
                st.session_state.chat_history.append({"role": "assistant", "content": full_response})
            except Exception as e:
                st.error(f"Hiba történt a generálás során: {e}")

# ==========================================
# 2. FÜL: NJK GENERÁTOR
# ==========================================
with tab2:
    st.subheader("Intelligens NJK Generátor")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        npc_race = st.selectbox("Faj", ["Ember", "Tünde (Elf)", "Törp (Dwarf)", "Félszerzet (Halfling)", "Sárkányszülött", "Tiefling", "Egyéb/Véletlen"])
    with col2:
        npc_role = st.selectbox("Szerep/Foglalkozás", ["Kereskedő", "Kocsmaros", "Őr", "Nemes", "Tolvaj", "Varázsló", "Véletlen"])
    with col3:
        npc_vibe = st.text_input("Hangulat / Jellemző (pl. Paranoiás, Vidám, Sötét titkot őriz)", "Barátságos, de kicsit kapzsi")

    if st.button("🎭 NJK Generálása", use_container_width=True):
        with st.spinner("Az istenek formálják a lelket..."):
            system_prompt = """
            Te egy kreatív D&D 5e NJK (NPC) író vagy. A felhasználó megadja az NJK paramétereit.
            Generálj egy jól játszható, egyedi NJK-t. A válaszod legyen strukturált markdown formátumú az alábbi pontokkal:
            - **Név:** (Egy hangulatos név)
            - **Kinézet:** (1-2 mondat a megjelenéséről)
            - **Személyiség és Motiváció:** (Mi mozgatja őt?)
            - **Titok vagy Különlegesség:** (Valami, amit a játékosok kideríthetnek róla)
            - **Szófordulat / Jellemző viselkedés:** (Hogyan játssza el a DM? Egy idézet, amit gyakran mond)
            """
            
            user_prompt = f"Kérlek generálj egy NJK-t: Faj: {npc_race}, Foglalkozás: {npc_role}, Hangulat/Extra: {npc_vibe}."

            try:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.8, # Magasabb temp, hogy kreatívabb legyen
                )
                st.success("NJK Sikeresen Legenerálva!")
                st.markdown(response.choices[0].message.content)
            except Exception as e:
                st.error(f"Hiba: {e}")

# ==========================================
# 3. FÜL: HELYSZÍN LEÍRÁS (Későbbi fejlesztés helye)
# ==========================================
with tab3:
    st.subheader("Dinamikus Helyszín Leírás (Read-Aloud)")
    st.info("Ide jön majd a kulcsszavas helyszíngenerátor. (Pl. Barlang, nyálkás falak, dobolás hangja a mélyből -> kész felolvasható leírás).")

import streamlit as st
from groq import Groq

# Globális modell beállítás
DEFAULT_MODEL = "llama3-70b-8192"

def get_groq_client():
    """Inicializálja és visszaadja a Groq klienst a secrets alapján."""
    try:
        return Groq(api_key=st.secrets["GROQ_API_KEY"])
    except KeyError:
        st.error("Hiányzik a Groq API kulcs! Kérlek, állítsd be a `.streamlit/secrets.toml` fájlban.")
        st.stop()

def ask_rules_lawyer(chat_history, model=DEFAULT_MODEL):
    """Lekérdezi a Rules Lawyer AI-t az eddigi chat történet alapján."""
    client = get_groq_client()
    
    messages = [
        {"role": "system", "content": "Te egy szakértő Dungeons & Dragons 5e Kalandmester (DM) asszisztens vagy. A feladatod, hogy pontos, tömör válaszokat adj az 5e szabályrendszer alapján. Hivatkozz az SRD-re, ha lehet. Légy objektív, de barátságos. Ha a szabály kétértelmű, javasolj egy igazságos DM döntést (Ruling). Magyarul válaszolj!"}
    ]
    # Konvertáljuk a Streamlit session_state formátumot a Groq által vártra
    messages.extend([{"role": m["role"], "content": m["content"]} for m in chat_history])

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.3, # Alacsony, hogy ragaszkodjon a szabályokhoz
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Hiba történt a generálás során: {e}"

def generate_npc(race, role, vibe, model=DEFAULT_MODEL):
    """Legenerál egy komplett D&D 5e NJK-t a paraméterek alapján."""
    client = get_groq_client()
    
    system_prompt = """
    Te egy kreatív D&D 5e NJK (NPC) író vagy. A felhasználó megadja az NJK paramétereit.
    Generálj egy jól játszható, egyedi NJK-t. A válaszod legyen strukturált markdown formátumú az alábbi pontokkal:
    - **Név:** (Egy hangulatos név)
    - **Kinézet:** (1-2 mondat a megjelenéséről)
    - **Személyiség és Motiváció:** (Mi mozgatja őt?)
    - **Titok vagy Különlegesség:** (Valami, amit a játékosok kideríthetnek róla)
    - **Szófordulat / Jellemző viselkedés:** (Hogyan játssza el a DM? Egy idézet, amit gyakran mond)
    """
    user_prompt = f"Kérlek generálj egy NJK-t: Faj: {race}, Foglalkozás: {role}, Hangulat/Extra: {vibe}."

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8, # Magasabb, hogy kreatívabb legyen
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Hiba történt az NJK generálásakor: {e}"

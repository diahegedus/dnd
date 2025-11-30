import streamlit as st
import random
import json
import os
from datetime import datetime

# Ellenőrizzük a csomagot
try:
    import google.generativeai as genai
    HAS_AI = True
except ImportError:
    HAS_AI = False

# --- 1. KONFIGURÁCIÓ ---
st.set_page_config(page_title="AI DM Pult", page_icon="🐉", layout="wide")

DEFAULT_ADVENTURE = {
    "title": "Üres Kaland",
    "description": "Tölts be egy JSON fájlt az oldalsávban!",
    "bestiary": {},
    "chapters": []
}

# --- 2. ÁLLAPOTOK ---
if 'dice_log' not in st.session_state: st.session_state.dice_log = []
if 'chat_history' not in st.session_state: st.session_state.chat_history = []
if 'active_adventure' not in st.session_state: st.session_state.active_adventure = DEFAULT_ADVENTURE
if 'inventory' not in st.session_state: st.session_state.inventory = []
if 'initiative' not in st.session_state: st.session_state.initiative = []

# --- 3. AI MOTOR (VÉGSŐ MENEDÉK: FLASH -> PRO) ---
def query_ai_with_search(prompt, api_key):
    if not api_key: return "⚠️ Nincs API kulcs! Állítsd be a Secrets-ben vagy írd be oldalt!"
    try:
        genai.configure(api_key=api_key)
        
        # Kaland Kontextus
        adv_context = json.dumps(st.session_state.active_adventure, ensure_ascii=False)
        inv_context = ", ".join(st.session_state.inventory)
        
        system_prompt = f"""
        Te egy Dungeon Master Segéd vagy.
        Források:
        1. KALAND: {adv_context}
        2. INVENTORY: {inv_context}
        """
        
        # 1. PRÓBA: 'gemini-1.5-flash' (Gyors és új)
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(f"{system_prompt}\n\nKÉRDÉS: {prompt}")
            return response.text
            
        except Exception as e_flash:
            # 2. PRÓBA: Ha a Flash nem található (404) vagy hiba van...
            try:
                model_old = genai.GenerativeModel('gemini-pro')
                response = model_old.generate_content(f"{system_prompt}\n\nKÉRDÉS: {prompt}")
                return f"⚠️ *[Régi modell (gemini-pro) aktív]*\n\n{response.text}"
            
            except Exception as e_old:
                return f"Kritikus AI Hiba: {str(e_old)}\n(Flash hiba: {str(e_flash)})"

    except Exception as e:
        return f"AI Konfigurációs Hiba: {str(e)}"

def roll_dice(sides, count=1):
    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls)
    st.session_state.dice_log.insert(0, f"{count}d{sides} ➔ {total}")

# --- 4. OLDALSÁV (DM TOOLS) ---
with st.sidebar:
    st.title("🛠️ DM Pult")
    
    # --- API KULCS KEZELÉS (ÚJ: SECRETS TÁMOGATÁS) ---
    # 1. Megnézzük, van-e a titkos tárolóban
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("🔐 Kulcs betöltve a Secrets-ből!")
    else:
        # 2. Ha nincs, akkor kérjük be kézzel
        api_key = st.text_input("Google API Kulcs", type="password", key="manual_api_key")
        if not api_key:
            st.warning("Nincs kulcs megadva.")
        else:
            st.success("Kulcs megadva!")

    # 1. TABOK
    tab_tools, tab_init, tab_ai_settings = st.tabs(["Kocka", "Harc", "Beállítás"])
    
    with tab_tools:
        st.subheader("🎲 Kockadobó")
        c1, c2, c3 = st.columns(3)
        if c1.button("d6", key="d6_btn"): roll_dice(6)
        if c2.button("d8", key="d8_btn"): roll_dice(8)
        if c3.button("d20", key="d20_btn"): roll_dice(20)
        for log in st.session_state.dice_log[:5]: st.caption(log)
        if st.button("Napló Törlése", key="clear_log"): 
            st.session_state.dice_log = []
            st.rerun()

    with tab_init:
        st.subheader("⚔️ Kezdeményezés")
        c_n, c_v = st.columns([2, 1])
        n = c_n.text_input("Név", key="init_name")
        v = c_v.number_input("Érték", key="init_val", value=0, step=1)
        
        if st.button("Hozzáad", key="add_init"):
            st.session_state.initiative.append({"n": n, "v": v})
            st.session_state.initiative.sort(key=lambda x: x['v'], reverse=True)
            st.rerun()
            
        st.divider()
        for idx, item in enumerate(st.session_state.initiative):
            cols = st.columns([3, 1])
            cols[0].write(f"**{item['v']}** - {item['n']}")
            if cols[1].button("X", key=f"del_init_{idx}"):
                st.session_state.initiative.pop(idx)
                st.rerun()

    with tab_ai_settings:
        st.markdown("[👉 Ingyenes kulcs (Google AI Studio)](https://aistudio.google.com/app/apikey)")
        uploaded_file = st.file_uploader("Kaland JSON", type="json")
        if uploaded_file:
            st.session_state.active_adventure = json.load(uploaded_file)
            st.success("Betöltve!")

    st.divider()
    
    # KINCSEK (INVENTORY)
    with st.expander("🎒 Kincsek"):
        for item in st.session_state.inventory: st.write(f"- {item}")
        new_item = st.text_input("Tárgy hozzáadása", key="new_loot_input")
        if st.button("Hozzáad", key="add_loot"):
            if new_item:
                st.session_state.inventory.append(new_item)
                st.rerun()

# --- 5. FŐ KÉPERNYŐ ---
st.title("🔮 AI Orákulum")

tab_chat, tab_view = st.tabs(["💬 Chat (AI)", "📖 Kaland Nézet"])

with tab_chat:
    if not HAS_AI:
        st.error("Nincs telepítve a `google-generativeai` csomag!")
    
    # Chat ürítése gomb
    if st.button("Chat Törlése", key="clear_chat"):
        st.session_state.chat_history = []
        st.rerun()

    for msg in st.session_state.chat_history:
        role = "user" if msg["role"] == "user" else "assistant"
        with st.chat_message(role):
            st.write(msg["content"])
            
    if prompt := st.chat_input("Pl: Mi van az 1-es szobában?"):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
            
        with st.chat_message("assistant"):
            with st.spinner("Keresés..."):
                response = query_ai_with_search(prompt, api_key)
                st.write(response)
                st.session_state.chat_history.append({"role": "assistant", "content": response})

with tab_view:
    adv = st.session_state.active_adventure
    st.header(adv.get("title", "Névtelen Kaland"))
    st.write(adv.get("description", ""))
    
    for idx, chapter in enumerate(adv.get("chapters", [])):
        with st.expander(chapter["title"]):
            st.markdown(f"**Leírás:** {chapter.get('text', '')}")
            st.info(f"DM Infó: {chapter.get('dm_notes', '')}")
            if "loot" in chapter:
                st.success(f"Loot: {', '.join(chapter['loot'])}")

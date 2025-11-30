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
st.set_page_config(page_title="AI DM Pult (Auto)", page_icon="🐉", layout="wide")

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

# --- 3. AI MOTOR (AUTO-DETECT & HIBAKEZELÉS) ---
def query_ai_auto(prompt, api_key):
    if not api_key:
        return "⚠️ Nincs API kulcs! Állítsd be a Secrets-ben vagy írd be oldalt!"

    try:
        genai.configure(api_key=api_key)

        # --- 1) MODELLEK LISTÁZÁSA ---
        try:
            raw_models = genai.list_models()
        except Exception as e:
            return f"⛔ Modellek listázása sikertelen: {str(e)}"

        valid_models = []
        for m in raw_models:
            # A Google néha dict-et ad vissza, néha property-t, ezt normalizáljuk
            methods = getattr(m, "supported_generation_methods", [])
            if isinstance(methods, dict):
                methods = list(methods.keys())

            # Csak azokat vesszük, amik tudnak contentet generálni
            if "generateContent" in methods:
                valid_models.append(m.name)

        if not valid_models:
            return "⛔ Nem találtam egyetlen olyan modellt sem, amely támogatná a generateContent metódust."

        # --- 2) PREFERÁLT MODELLEK (free tier kompatibilis) ---
        # A list_models() általában "models/..." formátumot ad, ezért így keressük
        preferred_order = [
            "models/gemini-1.5-flash-latest",
            "models/gemini-1.5-flash",
            "models/gemini-1.5-pro-latest",
            "models/gemini-1.5-pro",
            "gemini-1.5-flash", # Ha esetleg prefix nélkül jönne
            "gemini-1.5-pro",
        ]

        chosen_model = None
        for pref in preferred_order:
            if pref in valid_models:
                chosen_model = pref
                break

        # Ha semelyik preferált nem jó, akkor megyünk az első használhatóra
        if not chosen_model:
            chosen_model = valid_models[0]

        # --- 3) KONTEKSTUS ÖSSZERAKÁSA ---
        adv_context = json.dumps(st.session_state.active_adventure, ensure_ascii=False)
        inv_context = ", ".join(st.session_state.inventory)

        system_prompt = f"""
        Te egy Dungeon Master Segéd vagy.
        Források:
        1. KALAND: {adv_context}
        2. INVENTORY: {inv_context}
        """

        # --- 4) MODEL INICIALIZÁLÁS ---
        try:
            model = genai.GenerativeModel(chosen_model)
        except Exception as e:
            return f"⛔ A modell inicializálása sikertelen ({chosen_model}): {str(e)}"

        # --- 5) KÉRÉS ---
        try:
            response = model.generate_content(f"{system_prompt}\n\nKÉRDÉS: {prompt}")
            return f"✅ **[{chosen_model}]** válasza:\n\n{response.text}"
        except Exception as e:
            # Ha quota vagy region error → emberbarát üzenet
            err = str(e)

            if "429" in err or "quota" in err.lower():
                return (
                    "⛔ **Quota túllépve!**\n"
                    "Túl sok kérést küldtél a Google free tier API-ra. "
                    "Várj néhány percet vagy hozz létre új kulcsot a Google AI Studio-ban."
                )

            if "404" in err or "not found" in err.lower():
                return (
                    f"⛔ **A választott modell nem érhető el ebben a régióban vagy kulccsal:** {chosen_model}"
                )
            
            return f"Hiba a generálás során: {str(e)}"

    except Exception as e:
        return f"Váratlan hiba: {str(e)}"

def roll_dice(sides, count=1):
    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls)
    st.session_state.dice_log.insert(0, f"{count}d{sides} ➔ {total}")

# --- 4. OLDALSÁV (DM TOOLS) ---
with st.sidebar:
    st.title("🛠️ DM Pult")
    
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("🔐 Kulcs betöltve a Secrets-ből!")
    else:
        api_key = st.text_input("Google API Kulcs", type="password", key="manual_api_key")
        if not api_key:
            st.warning("Nincs kulcs megadva.")
        else:
            st.success("Manuális kulcs aktív!")

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
            with st.spinner("Modellek feltérképezése és válasz..."):
                response = query_ai_auto(prompt, api_key)
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

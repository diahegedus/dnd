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
            methods = getattr(m, "supported_generation_methods", [])
            if isinstance(methods, dict):
                methods = list(methods.keys())

            if "generateContent" in methods:
                valid_models.append(m.name)

        if not valid_models:
            return "⛔ Nem találtam egyetlen olyan modellt sem, amely támogatná a generateContent metódust."

        # --- 2) PREFERÁLT MODELLEK ---
        preferred_order = [
            "gemini-1.5-flash-latest",
            "gemini-1.5-flash",
            "gemini-1.5-pro-latest",
            "gemini-1.5-pro",
            "models/gemini-1.5-flash",
            "models/gemini-1.5-pro",
        ]

        chosen_model = None
        for pref in preferred_order:
            if pref in valid_models or f"models/{pref}" in valid_models:
                chosen_model = pref
                if f"models/{pref}" in valid_models:
                    chosen_model = f"models/{pref}"
                break

        if not chosen_model:
            chosen_model = valid_models[0]

        # --- 3) KONTEKSTUS ---
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
            err = str(e)
            if "429" in err or "quota" in err.lower():
                return "⛔ **Quota túllépve!**\nVárj néhány percet vagy hozz létre új kulcsot."
            if "404" in err or "not found" in err.lower():
                return f"⛔ **A választott modell nem érhető el:** {chosen_model}"
            return f"Hiba a generálás során: {str(e)}"

    except Exception as e:
        return f"Váratlan hiba: {str(e)}"

# --- KIBŐVÍTETT KOCKADOBÓ FÜGGVÉNY ---
def roll_dice(sides, count=1, modifier=0):
    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls) + modifier
    
    timestamp = datetime.now().strftime("%H:%M")
    mod_text = f" + {modifier}" if modifier != 0 else ""
    roll_details = ", ".join(map(str, rolls))
    
    # Különleges üzenet kritikus dobáshoz (csak d20-nál)
    crit_msg = ""
    if sides == 20 and count == 1:
        if rolls[0] == 20: crit_msg = " 🔥 KRITIKUS!"
        if rolls[0] == 1: crit_msg = " 💀 BALSORS!"

    log_entry = f"**{timestamp}** | {count}d{sides}{mod_text} ➔ [{roll_details}] = **{total}**{crit_msg}"
    
    # Hozzáadjuk a listához (elejére, hogy a legfrissebb legyen felül)
    st.session_state.dice_log.insert(0, log_entry)
    
    # Csak az utolsó 5-öt tartjuk meg (a listát vágjuk)
    if len(st.session_state.dice_log) > 5:
        st.session_state.dice_log = st.session_state.dice_log[:5]

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
    # ... a tab_init belsejében ...
st.subheader("⚔️ Kezdeményezés & HP")
c_n, c_v, c_hp = st.columns([2, 1, 1])
n = c_n.text_input("Név", key="init_name")
v = c_v.number_input("Init", key="init_val", value=0)
hp = c_hp.number_input("Max HP", key="init_hp", value=10)

if st.button("Hozzáad", key="add_init"):
    st.session_state.initiative.append({
        "n": n, "v": v, "hp": hp, "max_hp": hp, "conditions": []
    })
    st.session_state.initiative.sort(key=lambda x: x['v'], reverse=True)
    st.rerun()

st.divider()

# Lista megjelenítése szerkeszthető HP-val
for idx, item in enumerate(st.session_state.initiative):
    cols = st.columns([0.5, 2, 1.5, 1.5, 0.5]) # Init, Név, HP, Művelet, Törlés
    cols[0].write(f"**{item['v']}**")
    cols[1].write(f"**{item['n']}**")
    
    # HP Bar vizualizáció (színváltós)
    hp_percent = max(0, min(1.0, item['hp'] / item['max_hp'])) if item['max_hp'] > 0 else 0
    bar_color = "red" if hp_percent < 0.3 else "orange" if hp_percent < 0.6 else "green"
    cols[1].progress(hp_percent, text=f"{item['hp']} / {item['max_hp']} HP")

    # HP Módosítás
    dmg = cols[2].number_input("Mód", key=f"dmg_{idx}", value=0, label_visibility="collapsed")
    
    bt_cols = cols[3].columns(2)
    if bt_cols[0].button("🩸", key=f"hit_{idx}", help="Sebzés"):
        item['hp'] -= dmg
        st.rerun()
    if bt_cols[1].button("💚", key=f"heal_{idx}", help="Gyógyítás"):
        item['hp'] = min(item['max_hp'], item['hp'] + dmg)
        st.rerun()

    if cols[4].button("🗑️", key=f"del_{idx}"):
        st.session_state.initiative.pop(idx)
        st.rerun()
    
    # --- KIBŐVÍTETT KOCKA TAB ---
    with tab_tools:
        st.subheader("🎲 Kockadobó")
        
        # Beállítások egy sorban
        c_count, c_mod = st.columns(2)
        count = c_count.number_input("Db", min_value=1, value=1, step=1, key="dice_count")
        mod = c_mod.number_input("Mod (+/-)", value=0, step=1, key="dice_mod")
        
        st.write("Válassz kockát:")
        
        # Első sor (kisebb kockák)
        c1, c2, c3, c4 = st.columns(4)
        if c1.button("d4", use_container_width=True): roll_dice(4, count, mod)
        if c2.button("d6", use_container_width=True): roll_dice(6, count, mod)
        if c3.button("d8", use_container_width=True): roll_dice(8, count, mod)
        if c4.button("d10", use_container_width=True): roll_dice(10, count, mod)
        
        # Második sor (nagyobb kockák)
        c5, c6, c7 = st.columns(3)
        if c5.button("d12", use_container_width=True): roll_dice(12, count, mod)
        if c6.button("d20", use_container_width=True): roll_dice(20, count, mod)
        if c7.button("d100", use_container_width=True): roll_dice(100, count, mod)
        
        st.divider()
        st.caption("📜 Utolsó 5 dobás:")
        
        # Napló megjelenítése
        if st.session_state.dice_log:
            for log in st.session_state.dice_log:
                st.markdown(log)
        else:
            st.info("Még nem történt dobás.")
            
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
    
    # 1. CÍM ÉS META-ADATOK
    if "adventure_metadata" in adv:
        meta = adv["adventure_metadata"]
        st.header(meta.get("title", "Névtelen Kaland"))
        st.caption(f"Szint: {meta.get('level', '?')} | Műfaj: {meta.get('genre', '-')}")
        st.write(meta.get("summary", ""))
    else:
        st.header(adv.get("title", "Névtelen Kaland"))
        st.write(adv.get("description", ""))

    st.divider()

    # 2. SZEREPLŐK (NPC-K) MEGJELENÍTÉSE - EZ AZ ÚJ RÉSZ!
    if "npcs" in adv:
        with st.expander("👥 Szereplők és NJK-k"):
            for npc in adv["npcs"]:
                st.markdown(f"**{npc['name']}** ({npc.get('role', 'NJK')})")
                st.caption(npc.get('description', ''))
                st.write("---")

    # 3. FEJEZETEK MEGJELENÍTÉSE
    if "chapters" in adv:
        for chapter in adv["chapters"]:
            # Cím formázása (id kezelése)
            chap_title = chapter.get("title", "Fejezet")
            if "id" in chapter:
                # Ha 0. fejezet vagy Melléklet, máshogy jelenítjük meg
                chap_id = chapter['id']
                if chap_id == 0:
                    chap_title = f"ℹ️ {chap_title}"
                else:
                    chap_title = f"{chap_id}. {chap_title}"
                
            with st.expander(f"📖 {chap_title}"):
                if "location" in chapter:
                    st.subheader(f"📍 Helyszín: {chapter['location']}")
                
                # === ÚJ TÍPUS (Jelenetek / Scenes) ===
                if "scenes" in chapter:
                    for scene in chapter["scenes"]:
                        st.markdown("---") # Elválasztó vonal
                        
                        # Jelenet címe
                        scene_name = scene.get('title', 'Jelenet')
                        scene_type = scene.get('type', 'scene').upper()
                        
                        # Különleges ikonok a típusokhoz
                        icon = "🎬"
                        if scene_type == "COMBAT" or scene_type == "BOSS_FIGHT_FINAL": icon = "⚔️"
                        elif scene_type == "PUZZLE": icon = "🧩"
                        elif scene_type == "LOOT_AND_LORE": icon = "💰"
                        elif scene_type == "INTRO": icon = "📜"
                        
                        st.markdown(f"#### {icon} {scene_name}")

                        # 1. Felolvasandó szöveg (Kék)
                        if "read_aloud" in scene:
                            st.info(f"🗣️ **Felolvasandó:**\n\n{scene['read_aloud']}")
                        
                        # 2. DM Infók (Piros)
                        if "dm_notes" in scene:
                            st.error(f"🕵️ **DM Info:** {scene['dm_notes']}")

                        # 3. Tutorial tippek (Szürke)
                        if "tutorial_tip" in scene:
                            st.caption(f"💡 *Tipp:* {scene['tutorial_tip']}")

                        # 4. Mechanika és Ellenségek (Két oszlop)
                        c1, c2 = st.columns(2)
                        with c1:
                            if "mechanics" in scene:
                                st.warning(f"⚙️ **Szabályok:**\n\n{scene['mechanics']}")
                            if "check" in scene:
                                # Ha a check objektum vagy szöveg
                                check_data = scene['check']
                                if isinstance(check_data, dict):
                                    st.write(f"🎲 **Próba:** {check_data.get('skill')} DC {check_data.get('dc')}")
                                    st.caption(f"Siker: {check_data.get('success')}")
                                else:
                                    st.write(f"🎲 **Próba:** {check_data}")
                                    
                            if "options" in scene:
                                st.write("🔹 **Döntési lehetőségek:**")
                                for opt in scene['options']:
                                    st.write(f"- **{opt['method']}**: {opt['check']}")
                            
                            # Boss fázisok kezelése
                            if "phases" in scene:
                                st.write("🔥 **Fázisok:**")
                                for phase in scene['phases']:
                                    st.markdown(f"**{phase['name']}**")
                                    st.caption(phase.get('description', ''))
                                    if 'trigger' in phase: st.code(f"Trigger: {phase['trigger']}")
                                    if 'legendary_actions' in phase: st.write(f"Legendary: {phase['legendary_actions']}")
                        
                        with c2:
                            if "enemies" in scene:
                                st.write("⚔️ **Ellenségek:**")
                                for enemy in scene["enemies"]:
                                    if isinstance(enemy, dict):
                                        st.code(f"{enemy.get('name')} (x{enemy.get('count', 1)})\n{enemy.get('stat_block', '')}\n{enemy.get('notes', '')}")
                                    else:
                                        st.code(str(enemy))
                            
                            if "environment_effects" in scene:
                                st.write("🌪️ **Környezeti Hatások:**")
                                for eff in scene["environment_effects"]:
                                    st.write(f"- d4={eff['roll']}: {eff['name']} ({eff['effect']})")
                            
                            if "environment" in scene:
                                st.write(f"🌳 **Terep:** {scene['environment']}")

                        # 5. Handoutok
                        if "handout" in scene:
                            h = scene["handout"]
                            st.success(f"📩 **Handout:** {h.get('title', '')}\n\n*{h.get('text', '')}*")
                        
                        # 6. Loot
                        if "loot" in scene:
                            loot_data = scene['loot']
                            if isinstance(loot_data, list):
                                st.success(f"💰 **Zsákmány:** {', '.join(loot_data)}")
                            else:
                                st.success(f"💰 **Zsákmány:** {loot_data}")

                # === RÉGI TÍPUS (Biztonsági tartalék) ===
                else:
                    if 'text' in chapter: st.markdown(chapter['text'])
                    if 'dm_notes' in chapter: st.error(f"DM Infó: {chapter['dm_notes']}")
                    if "loot" in chapter: st.success(f"Loot: {', '.join(chapter['loot'])}")

    else:
        st.warning("Ez a kalandfájl nem tartalmaz fejezeteket.")

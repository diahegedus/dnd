import streamlit as st
import random
import pandas as pd
import json
from datetime import datetime

# --- 1. KONFIGURÁCIÓ & DEFAULT ADATOK ---
st.set_page_config(
    page_title="Univerzális RPG Motor",
    page_icon="🐉",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Alapértelmezett "Demo" kaland
DEFAULT_ADVENTURE = {
    "title": "Demó Kaland: A Goblin Pince",
    "description": "Egy rövid példa kaland a rendszer tesztelésére.",
    "bestiary": {
        "Goblin": {"AC": 15, "HP": 7, "MaxHP": 7, "Stats": "DEX +2", "Actions": "Szablya (+4, 1d6+2)", "Image": "👺"},
        "Warg": {"AC": 13, "HP": 18, "MaxHP": 18, "Stats": "STR +3", "Actions": "Harapás (+5, 2d4+3)", "Image": "🐺"}
    },
    "chapters": [
        {
            "title": "1. A Bejárat",
            "text": "Egy sötét barlang szájához értek. Halk morgás hallatszik bentről.",
            "dm_notes": "A morgás csak szélzaj, de ijeszd meg őket. Perception DC 12.",
            "encounters": [],
            "loot": ["Fáklya", "Kovakő"]
        },
        {
            "title": "2. Az Őrszemek",
            "text": "Két goblin vitatkozik egy sült patkányon. Észrevesznek titeket!",
            "dm_notes": "Ha a játékosok lopakodnak (Stealth DC 14), meglepetés körük van.",
            "encounters": [{"name": "Goblin", "count": 2}],
            "loot": ["Görbe kard", "3 arany"]
        }
    ]
}

# --- 2. ÁLLAPOT KEZELÉS ---
if 'dice_log' not in st.session_state: st.session_state.dice_log = []
if 'inventory' not in st.session_state: st.session_state.inventory = []
if 'initiative' not in st.session_state: st.session_state.initiative = [] # Lista dict-ekből: {'n': név, 'v': érték, 's': status}
if 'active_adventure' not in st.session_state: st.session_state.active_adventure = DEFAULT_ADVENTURE

# Bővített Játékos Adatbázis (Party Tracker)
if 'players' not in st.session_state:
    st.session_state.players = pd.DataFrame([
        {"Név": "Játékos 1", "AC": 14, "HP": 20, "MaxHP": 20, "PP (Wis)": 12, "DC": 13, "Cond": ""},
        {"Név": "Játékos 2", "AC": 18, "HP": 25, "MaxHP": 25, "PP (Wis)": 10, "DC": 11, "Cond": ""}
    ])

# --- 3. LOGIKA & FÜGGVÉNYEK ---

def load_adventure(json_file):
    try:
        data = json.load(json_file)
        required_keys = ["title", "bestiary", "chapters"]
        if all(key in data for key in required_keys):
            st.session_state.active_adventure = data
            st.toast(f"Kaland betöltve: {data['title']}", icon="✅")
        else:
            st.error("Hibás JSON! Hiányzó kulcsok: title, bestiary, chapters.")
    except Exception as e:
        st.error(f"Hiba: {e}")

def roll_dice(sides, count=1, modifier=0):
    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls) + modifier
    details = f"[{', '.join(map(str, rolls))}]"
    mod_text = f" + {modifier}" if modifier != 0 else ""
    timestamp = datetime.now().strftime("%H:%M")
    
    crit = ""
    if sides == 20 and count == 1:
        if rolls[0] == 20: crit = " 🔥 KRITIKUS!"
        if rolls[0] == 1: crit = " 💀 BALSORS!"
        
    log_entry = f"**{timestamp}** | {count}d{sides}{mod_text} ➔ {details} = **{total}**{crit}"
    st.session_state.dice_log.insert(0, log_entry)
    if len(st.session_state.dice_log) > 15: st.session_state.dice_log.pop()

def render_combat(enemy_name, count, chapter_idx):
    bestiary = st.session_state.active_adventure.get("bestiary", {})
    if enemy_name not in bestiary:
        st.error(f"Hiba: '{enemy_name}' nincs a bestiáriumban!")
        return
        
    data = bestiary[enemy_name]
    st.markdown(f"#### ⚔️ {count}x {enemy_name}")
    
    with st.expander(f"📊 {enemy_name} Statisztikák (AC: {data.get('AC', 10)})", expanded=False):
        c1, c2 = st.columns([1, 2])
        with c1:
            st.metric("AC", data.get('AC', 10))
            st.metric("HP", data.get('MaxHP', 10))
        with c2:
            st.info(f"Stats: {data.get('Stats', '-')}")
            st.error(f"Action: {data.get('Actions', '-')}")

    cols = st.columns(min(count, 4))
    for i in range(count):
        unique_key = f"hp_ch{chapter_idx}_{enemy_name}_{i}"
        if unique_key not in st.session_state:
            st.session_state[unique_key] = data.get("MaxHP", 10)
            
        with cols[i % 4]:
            current_hp = st.session_state[unique_key]
            st.markdown(f"**{data.get('Image','💀')} #{i+1}**")
            
            sub_c1, sub_c2, sub_c3 = st.columns([1,2,1])
            if sub_c1.button("➖", key=f"dec_{unique_key}"):
                st.session_state[unique_key] = max(0, current_hp - 1)
                st.rerun()
            sub_c2.markdown(f"<div style='text-align:center; font-weight:bold; font-size:1.2em'>{current_hp}</div>", unsafe_allow_html=True)
            if sub_c3.button("➕", key=f"inc_{unique_key}"):
                st.session_state[unique_key] = current_hp + 1
                st.rerun()
            
            # HP Bar színkódolva
            max_hp = data.get("MaxHP", 10)
            ratio = current_hp / max_hp
            bar_color = "red" if ratio < 0.3 else "orange" if ratio < 0.6 else "green"
            st.progress(max(0.0, min(1.0, ratio)))

# --- 4. CSS STÍLUS ---
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #c9d1d9; }
    h1, h2, h3 { color: #58a6ff; font-family: 'Segoe UI', sans-serif; }
    .read-box { background: #161b22; border-left: 5px solid #58a6ff; padding: 15px; margin: 10px 0; border-radius: 4px; color: #e6edf3; font-style: italic;}
    .dm-box { background: #21262d; border: 1px dashed #d29922; padding: 10px; margin: 10px 0; border-radius: 4px; color: #d29922; }
    .loot-box { background: #0d1117; border: 1px solid #3fb950; padding: 10px; color: #3fb950; border-radius: 4px; }
    .stButton>button { width: 100%; border-radius: 4px; }
    /* Táblázat kompakt nézethez */
    div[data-testid="stDataFrame"] { width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- 5. OLDALSÁV (DM ESZKÖZÖK) ---
with st.sidebar:
    st.title("🛠️ DM Pult")
    
    # 1. TABOK A FUNKCIÓKNAK
    tab_tools, tab_party, tab_init, tab_ref = st.tabs(["Kocka", "Party", "Harc", "Lexikon"])
    
    # --- TAB: KOCKA ---
    with tab_tools:
        st.subheader("🎲 Kockadobó")
        col_count, col_mod = st.columns(2)
        cnt = col_count.number_input("Db", 1, 10, 1)
        mod = col_mod.number_input("Mod", -10, 20, 0)
        c1, c2, c3 = st.columns(3)
        if c1.button("d6"): roll_dice(6, cnt, mod)
        if c2.button("d8"): roll_dice(8, cnt, mod)
        if c3.button("d20"): roll_dice(20, cnt, mod)
        
        st.caption("Napló:")
        for log in st.session_state.dice_log[:5]: st.markdown(log)
        if st.button("Törlés"): 
            st.session_state.dice_log = []
            st.rerun()
            
        # Fájl feltöltés ide került
        st.divider()
        uploaded_file = st.file_uploader("📂 Kaland Betöltése", type="json")
        if uploaded_file is not None: load_adventure(uploaded_file)

    # --- TAB: PARTY TRACKER (DDB Kiváltó) ---
    with tab_party:
        st.subheader("személyzet Állapota")
        st.caption("Szerkeszthető táblázat. Írd át a HP-t vagy Kondíciót harc közben!")
        
        # Oszlop konfiguráció a szebb megjelenésért
        column_cfg = {
            "HP": st.column_config.NumberColumn("HP", min_value=0, step=1),
            "MaxHP": st.column_config.NumberColumn("Max", min_value=1, step=1),
            "PP (Wis)": st.column_config.NumberColumn("Passzív Észlelés", help="Passive Perception"),
            "DC": st.column_config.NumberColumn("Spell DC"),
            "Cond": st.column_config.SelectboxColumn("Kondíció", options=["", "Blinded", "Charmed", "Frightened", "Grappled", "Paralyzed", "Poisoned", "Prone", "Stunned", "Unconscious"])
        }
        
        edited_df = st.data_editor(
            st.session_state.players, 
            num_rows="dynamic", 
            hide_index=True,
            column_config=column_cfg,
            key="party_editor"
        )
        st.session_state.players = edited_df

    # --- TAB: HARC & INICIATÍVA ---
    with tab_init:
        st.subheader("⚔️ Kezdeményezés")
        c_n, c_v = st.columns([2, 1])
        n = c_n.text_input("Név", key="in_n")
        v = c_v.number_input("Érték", key="in_v", value=0, step=1)
        
        if st.button("Hozzáad"):
            st.session_state.initiative.append({"n": n, "v": v, "s": ""})
            st.session_state.initiative.sort(key=lambda x: x['v'], reverse=True)
            st.rerun()
            
        st.divider()
        for idx, item in enumerate(st.session_state.initiative):
            col1, col2, col3 = st.columns([1, 3, 1])
            col1.markdown(f"**{item['v']}**")
            
            # Név és státusz kijelzése
            status_icon = f" ({item['s']})" if item['s'] else ""
            col2.markdown(f"{item['n']} {status_icon}")
            
            # Státusz állítás menü (popover)
            with col2.popover("📝"):
                item['s'] = st.selectbox("Státusz", ["", "👑 Boss", "☠️ Halott", "💤 Altatva", "👀 Vak", "🩸 Vérzik"], key=f"stat_{idx}")
                if st.button("Frissít", key=f"upd_{idx}"): st.rerun()

            if col3.button("X", key=f"del_{idx}"):
                st.session_state.initiative.pop(idx)
                st.rerun()
        
        if st.button("Lista Törlése"):
            st.session_state.initiative = []
            st.rerun()

    # --- TAB: LEXIKON (ÚJ!) ---
    with tab_ref:
        st.subheader("📚 Gyors Szabályok")
        search = st.text_input("Keresés (pl. Blinded, Action)", "")
        
        # Ez lehetne egy külön JSON is, de most hardcoded példa
        rules = {
            "Blinded": "Automatikusan elvét minden látás alapú próbát. Támadások ellene Előnnyel, saját támadásai Hátránnyal.",
            "Prone": "A földön fekszik. Felállni a mozgás fele. Közelharci támadás ellene Előnnyel, távolsági Hátránnyal.",
            "Grappled": "A sebesség 0. A kondíció véget ér, ha a megragadó harcképtelen lesz.",
            "Restrained": "Sebesség 0. Támadások ellene Előnnyel, sajátjai Hátránnyal. DEX mentők Hátránnyal.",
            "Dodge": "A köröd kezdetéig minden támadás ellened Hátránnyal történik (ha látod a támadót). DEX mentők Előnnyel.",
            "Dash": "Dupla mozgássebességet kapsz a körre.",
            "Disengage": "A mozgásod nem vált ki megszakító támadást (Opportunity Attack) ebben a körben.",
            "Help": "Előnyt adsz egy társadnak a következő próbájára vagy támadására."
        }
        
        found = False
        for key, val in rules.items():
            if search.lower() in key.lower():
                st.markdown(f"**{key}:** {val}")
                st.divider()
                found = True
        
        if not found and search:
            st.warning("Nincs találat a lexikonban.")

    # Inventory a sidebar alján
    with st.expander("🎒 Kincsek"):
        for item in st.session_state.inventory: st.write(f"- {item}")
        new_item = st.text_input("Tárgy hozzáadása")
        if st.button("Hozzáad"):
            st.session_state.inventory.append(new_item)
            st.rerun()

# --- 6. FŐ TARTALOM ---
adventure = st.session_state.active_adventure

st.title(adventure.get("title", "Névtelen Kaland"))
if "description" in adventure:
    st.caption(adventure["description"])

# Fejezet választó
chapter_titles = [ch["title"] for ch in adventure["chapters"]]
selected_chapter_name = st.sidebar.radio("📖 Fejezetek", chapter_titles)

current_chapter = next((ch for ch in adventure["chapters"] if ch["title"] == selected_chapter_name), None)
current_chapter_idx = adventure["chapters"].index(current_chapter)

if current_chapter:
    st.header(current_chapter["title"])
    
    if "text" in current_chapter and current_chapter["text"]:
        st.markdown(f'<div class="read-box">🗣️ <b>OLVASD FEL:</b><br>{current_chapter["text"]}</div>', unsafe_allow_html=True)
    
    if "dm_notes" in current_chapter and current_chapter["dm_notes"]:
        st.markdown(f'<div class="dm-box">🧙‍♂️ <b>DM INFÓ:</b> {current_chapter["dm_notes"]}</div>', unsafe_allow_html=True)
    
    if "encounters" in current_chapter:
        for encounter in current_chapter["encounters"]:
            st.divider()
            render_combat(encounter["name"], encounter.get("count", 1), current_chapter_idx)
            
    if "loot" in current_chapter and current_chapter["loot"]:
        st.divider()
        st.markdown("#### 💎 Zsákmány a helyszínen")
        cols = st.columns(len(current_chapter["loot"]))
        for idx, item in enumerate(current_chapter["loot"]):
            if item not in st.session_state.inventory:
                if cols[idx % 3].button(f"Felvesz: {item}", key=f"loot_{current_chapter_idx}_{idx}"):
                    st.session_state.inventory.append(item)
                    st.rerun()
            else:
                cols[idx % 3].success(f"✅ {item} (Nálatok)")
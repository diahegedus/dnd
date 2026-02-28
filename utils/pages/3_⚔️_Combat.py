import streamlit as st
import pandas as pd
import random
import re

st.set_page_config(page_title="Combat Tracker", page_icon="⚔️", layout="wide")
st.title("⚔️ Harcrendszer és Kezdeményezés")

# ==========================================
# 1. ÁLLAPOT INICIALIZÁLÁSA
# ==========================================
# Ha valaki egyből ide kattint, ne szálljon el a kód
if "players" not in st.session_state:
    st.session_state.players = {}

if "combatants" not in st.session_state:
    st.session_state.combatants = []

if "round_number" not in st.session_state:
    st.session_state.round_number = 1

if "current_turn" not in st.session_state:
    st.session_state.current_turn = 0

if "dice_history" not in st.session_state:
    st.session_state.dice_history = []

# ==========================================
# 2. SEGÉDFÜGGVÉNYEK
# ==========================================
def roll_dice(dice_str):
    """Szöveges kockadobás értelmezése (pl. '2d6+3', '1d20-1')"""
    # Eltávolítjuk a szóközöket és kisbetűssé tesszük
    dice_str = dice_str.replace(" ", "").lower()
    match = re.match(r'(\d+)d(\d+)(?:([+-])(\d+))?', dice_str)
    
    if not match:
        return None, "Hibás formátum! Használj ilyet: 1d20, 2d6+3, 1d8-1"
    
    count = int(match.group(1))
    sides = int(match.group(2))
    sign = match.group(3)
    modifier = match.group(4)
    
    if count > 100 or sides > 1000:
        return None, "Túl sok kocka vagy túl sok oldal!"
        
    rolls = [random.randint(1, sides) for _ in range(count)]
    total = sum(rolls)
    
    if modifier:
        if sign == '+':
            total += int(modifier)
        elif sign == '-':
            total -= int(modifier)
            
    mod_str = f" {sign} {modifier}" if modifier else ""
    return total, f"**{dice_str}** ➡️ {rolls}{mod_str} = **{total}**"

def next_turn():
    """Lépteti a kört és a kezdeményezést"""
    if not st.session_state.combatants:
        return
        
    st.session_state.current_turn += 1
    # Ha körbeértünk, új harci kör kezdődik
    if st.session_state.current_turn >= len(st.session_state.combatants):
        st.session_state.current_turn = 0
        st.session_state.round_number += 1

# ==========================================
# 3. FELÜLET KIALAKÍTÁSA (Két oszlop)
# ==========================================
col_tracker, col_tools = st.columns([2, 1])

# --- BAL OSZLOP: KEZDEMÉNYEZÉS KÖVETŐ ---
with col_tracker:
    st.header(f"⏱️ Harci Kör: {st.session_state.round_number}")
    
    # Harcosok hozzáadása
    with st.expander("➕ Új harcos hozzáadása", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        new_name = c1.text_input("Név", key="new_name")
        new_init = c2.number_input("Kezdeményezés", value=10, key="new_init")
        new_hp = c3.number_input("HP", value=10, key="new_hp")
        new_ac = c4.number_input("AC (Vért)", value=10, key="new_ac")
        
        btn_col1, btn_col2 = st.columns(2)
        if btn_col1.button("Hozzáadás", use_container_width=True):
            if new_name:
                st.session_state.combatants.append({
                    "Név": new_name, "Kezdeményezés": new_init, "HP": new_hp, "AC": new_ac
                })
                # Újrarendezzük csökkenő sorrendbe kezdeményezés alapján
                st.session_state.combatants = sorted(st.session_state.combatants, key=lambda x: x["Kezdeményezés"], reverse=True)
                st.rerun()
                
        if btn_col2.button("Játékosok áthúzása a Dashboardról", use_container_width=True):
            if st.session_state.players:
                for p_name, p_data in st.session_state.players.items():
                    # Ellenőrizzük, hogy nincs-e már bent
                    if not any(c["Név"] == p_name for c in st.session_state.combatants):
                        st.session_state.combatants.append({
                            "Név": p_name, 
                            "Kezdeményezés": 0, # Ezt majd a DM beírja
                            "HP": p_data["hp"], 
                            "AC": p_data["ac"]
                        })
                st.session_state.combatants = sorted(st.session_state.combatants, key=lambda x: x["Kezdeményezés"], reverse=True)
                st.rerun()

    # Harci sorrend megjelenítése (Interaktív táblázat)
    if st.session_state.combatants:
        # Gombok a vezérléshez
        c_prev, c_next, c_clear = st.columns([1, 2, 1])
        if c_next.button("⏭️ Következő Kör (Next Turn)", type="primary", use_container_width=True):
            next_turn()
            st.rerun()
        if c_clear.button("🗑️ Harc vége (Törlés)"):
            st.session_state.combatants = []
            st.session_state.round_number = 1
            st.session_state.current_turn = 0
            st.rerun()

        # Vizuális jelzés, kinek a köre van
        st.markdown("### Sorrend")
        
        # A st.data_editor-t használjuk itt is, de dinamikusan formázzuk
        # DataFrame-be rakjuk a szebb megjelenítésért
        df = pd.DataFrame(st.session_state.combatants)
        
        # Hozzáadunk egy vizuális mutatót az aktív körhöz
        df.insert(0, "Aktív", ["🟢" if i == st.session_state.current_turn else "" for i in range(len(df))])
        
        edited_combatants = st.data_editor(
            df,
            hide_index=True,
            use_container_width=True,
            disabled=["Aktív"], # Az aktív oszlopot nem szerkesztheti manuálisan
            key="combat_editor"
        )
        
        # Visszamentjük a szerkesztett adatokat (pl. ha valaki sebződött)
        if not edited_combatants.equals(df):
            # Frissítjük a session state-t a módosított adatokkal, de az "Aktív" oszlopot eldobjuk
            st.session_state.combatants = edited_combatants.drop(columns=["Aktív"]).to_dict('records')
            # Visszaírjuk a játékosok HP-ját a globális state-be, ha az változott
            for combatant in st.session_state.combatants:
                if combatant["Név"] in st.session_state.players:
                    st.session_state.players[combatant["Név"]]["hp"] = combatant["HP"]
            # Itt nem hívunk rerun-t, mert végtelen ciklust okozhat a data_editor-ral, 
            # de a háttérben már frissültek az adatok.

    else:
        st.info("A harcmező üres. Adj hozzá résztvevőket!")

# --- JOBB OSZLOP: KOCKADOBÓ ÉS SZÖRNYEK ---
with col_tools:
    st.subheader("🎲 DM Kockadobó (Rejtett)")
    
    dice_input = st.text_input("Makró (pl. 1d20+5, 8d6):", value="1d20", key="dice_input")
    if st.button("Dobás!", use_container_width=True):
        total, result_text = roll_dice(dice_input)
        if total is not None:
            # Hozzáadjuk a történethez a legújabbat előre
            st.session_state.dice_history.insert(0, result_text)
            # Maximum 5 dobást tartunk meg
            st.session_state.dice_history = st.session_state.dice_history[:5]
        else:
            st.error(result_text)
            
    # Dobástörténet megjelenítése
    for hist in st.session_state.dice_history:
        st.info(hist)

    st.divider()
    
    st.subheader("🐉 Gyors Szörny Statisztika")
    st.caption("Későbbi fejlesztés: Open5e API integráció vagy helyi adatbázis (JSON).")
    search_monster = st.text_input("Szörny keresése (Demó):", placeholder="pl. Goblin")
    
    if search_monster.lower() == "goblin":
        st.markdown("""
        **Goblin** (Small humanoid)
        - **AC:** 15 (Leather armor, shield)
        - **HP:** 7 (2d6)
        - **Speed:** 30 ft.
        - **STR:** 8 (-1) | **DEX:** 14 (+2) | **CON:** 10 (+0)
        - **Skills:** Stealth +6
        - **Senses:** Darkvision 60 ft., Passive Perception 9
        - **Nimble Escape:** The goblin can take the Disengage or Hide action as a bonus action.
        - **Scimitar:** +4 to hit, 1d6 + 2 slashing dmg.
        - **Shortbow:** +4 to hit, 1d6 + 2 piercing dmg.
        """)
    elif search_monster:
        st.warning("Szörny nem található a demó adatbázisban. (Próbáld: 'Goblin')")

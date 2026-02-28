import streamlit as st
import pandas as pd

st.set_page_config(page_title="Party Dashboard", page_icon="🛡️", layout="wide")
st.title("🛡️ Party Dashboard & Játékos Követő")

# ==========================================
# 1. ÁLLAPOT INICIALIZÁLÁSA (Session State)
# ==========================================
# Alapértelmezett játékos adatok (teszteléshez)
default_players = {
    "Eldor": {"max_hp": 45, "hp": 45, "ac": 16, "pp": 14, "conditions": "Nincs"},
    "Lyra": {"max_hp": 32, "hp": 28, "ac": 14, "pp": 16, "conditions": "Nincs"},
    "Grom": {"max_hp": 65, "hp": 12, "ac": 18, "pp": 11, "conditions": "Mérgezett"}
}

if "players" not in st.session_state:
    st.session_state.players = default_players

if "party_stash" not in st.session_state:
    # Egy Pandas DataFrame tökéletes a szerkeszthető kincstárhoz
    st.session_state.party_stash = pd.DataFrame([
        {"Tárgy": "Gyógyító ital (Potion of Healing)", "Mennyiség": 3, "Súly (lbs)": 1.5},
        {"Tárgy": "Aranypénz (gp)", "Mennyiség": 450, "Súly (lbs)": 9.0},
        {"Tárgy": "Varázslatos kötél", "Mennyiség": 1, "Súly (lbs)": 5.0}
    ])

# ==========================================
# 2. D&D BEYOND IMPORTÁLÓ (Kísérleti)
# ==========================================
with st.expander("🔗 D&D Beyond Karakter Importálása (JSON)", expanded=False):
    st.markdown("Illeszd be a karakter publikus JSON linkjét (pl. `https://character-service.dndbeyond.com/character/v5/character/ID`).")
    col1, col2 = st.columns([3, 1])
    with col1:
        ddb_url = st.text_input("D&D Beyond URL", label_visibility="collapsed", placeholder="https://...")
    with col2:
        if st.button("Karakter Betöltése", use_container_width=True):
            if ddb_url:
                st.info("Későbbi fejlesztés: Itt a `utils/dnd_beyond_parser.py` fogja feldolgozni a JSON-t és betenni a `st.session_state.players`-be.")
            else:
                st.warning("Kérlek adj meg egy URL-t!")

st.divider()

# ==========================================
# 3. JÁTÉKOS KÖVETŐ & PIHENŐK
# ==========================================
col_header, col_rest1, col_rest2 = st.columns([2, 1, 1])
with col_header:
    st.subheader("Karakterek Állapota")
with col_rest1:
    if st.button("⛺ Rövid Pihenő (Short Rest)", use_container_width=True):
        st.toast("A játékosok elkölthetik a Hit Dice-aikat!")
with col_rest2:
    if st.button("🔥 Hosszú Pihenő (Long Rest)", use_container_width=True):
        # Mindenki visszakapja a Max HP-ját
        for p in st.session_state.players:
            st.session_state.players[p]["hp"] = st.session_state.players[p]["max_hp"]
        st.success("A csapat kipihente magát. HP és spell slotok visszaállítva!")
        st.rerun() # Frissíti a UI-t azonnal

# Játékos kártyák kirajzolása (dinamikus oszlopszám)
cols = st.columns(len(st.session_state.players))

for idx, (name, stats) in enumerate(st.session_state.players.items()):
    with cols[idx]:
        with st.container(border=True):
            st.markdown(f"### {name}")
            
            # HP sáv (vizuális visszajelzés)
            hp_percent = max(0, min(100, int((stats['hp'] / stats['max_hp']) * 100)))
            
            # Színváltás HP alapján (Streamlit progress bar natívan kék, de a metrika ad egy jó vizuált)
            st.progress(hp_percent, text=f"HP: {stats['hp']} / {stats['max_hp']}")
            
            # AC és PP
            c1, c2 = st.columns(2)
            c1.metric("AC (Vért)", stats['ac'])
            c2.metric("Passzív Észl.", stats['pp'])
            
            # Gyors HP módosító
            hp_mod = st.number_input(f"Sebzés/Gyógyulás ({name})", value=0, step=1, key=f"hp_mod_{name}")
            if hp_mod != 0:
                if st.button("Alkalmaz", key=f"apply_{name}", use_container_width=True):
                    st.session_state.players[name]["hp"] += hp_mod
                    # Ne engedjük a Max HP fölé (ha csak nem Temp HP, de azt most hanyagoljuk)
                    if st.session_state.players[name]["hp"] > st.session_state.players[name]["max_hp"]:
                         st.session_state.players[name]["hp"] = st.session_state.players[name]["max_hp"]
                    st.rerun()
            
            # Állapot
            st.session_state.players[name]["conditions"] = st.text_input("Állapot", stats['conditions'], key=f"cond_{name}")

st.divider()

# ==========================================
# 4. KÖZÖS KINCSTÁR (Party Stash) & SÚLY
# ==========================================
st.subheader("💰 Közös Kincstár (Party Stash) és Súly")
st.markdown("Kattints a táblázatba a szerkesztéshez! Új sor hozzáadásához kattints az utolsó sor alá.")

# Szerkeszthető adatkeret (Data Editor) - zseniális Streamlit funkció!
edited_df = st.data_editor(
    st.session_state.party_stash, 
    num_rows="dynamic", # Lehet új sorokat hozzáadni / törölni
    use_container_width=True,
    key="stash_editor"
)

# Frissítjük a session state-t a szerkesztett táblázattal
st.session_state.party_stash = edited_df

# Súly kiszámítása (Mennyiség * Súly (lbs))
try:
    total_weight = (edited_df["Mennyiség"] * edited_df["Súly (lbs)"]).sum()
    st.info(f"⚖️ **Teljes súly a kincstárban:** {total_weight:.1f} lbs")
    if total_weight > 500: # Csak egy fiktív limit figyelmeztetésnek
        st.warning("⚠️ Nehéz a zsák! Lehet, hogy kellene egy Bag of Holding vagy egy öszvér...")
except KeyError:
    st.error("Hiba a súlyszámításban. Kérlek ne nevezd át az oszlopokat!")

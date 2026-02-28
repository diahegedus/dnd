import streamlit as st
import pandas as pd
from streamlit_agraph import agraph, Node, Edge, Config

st.set_page_config(page_title="Worldbuilding", page_icon="📖", layout="wide")
st.title("📖 Világépítés és Kampány Menedzsment")

# ==========================================
# 1. ÁLLAPOT INICIALIZÁLÁSA
# ==========================================
if "calendar" not in st.session_state:
    st.session_state.calendar = {"nap": 14, "honap": "Tavasz", "idojaras": "Enyhe eső", "ido": "14:30"}

if "factions" not in st.session_state:
    st.session_state.factions = pd.DataFrame([
        {"Frakció": "A Korona Őrsége", "Hírnév (Reputation)": 10, "Státusz": "Szövetséges", "Vezető": "Lord Kaelen"},
        {"Frakció": "Zhentarim (Fekete Hálózat)", "Hírnév (Reputation)": -5, "Státusz": "Gyanakvó", "Vezető": "Ismeretlen"},
        {"Frakció": "Tolvajcéh", "Hírnév (Reputation)": 0, "Státusz": "Semleges", "Vezető": "A Keresztapa"}
    ])

if "graph_nodes" not in st.session_state:
    # Alapértelmezett csomópontok (Szereplők / Frakciók)
    st.session_state.graph_nodes = [
        {"id": "Party", "label": "Kalandorok", "color": "#FFD700", "size": 25, "shape": "star"},
        {"id": "King", "label": "A Király", "color": "#4169E1", "size": 20, "shape": "dot"},
        {"id": "Zhentarim", "label": "Zhentarim", "color": "#8B0000", "size": 20, "shape": "dot"},
        {"id": "Bob", "label": "Bob, a Kocsmáros", "color": "#228B22", "size": 15, "shape": "dot"}
    ]

if "graph_edges" not in st.session_state:
    # Alapértelmezett kapcsolatok (Élek)
    st.session_state.graph_edges = [
        {"source": "Party", "target": "Bob", "label": "Törzsvendégek"},
        {"source": "Party", "target": "King", "label": "Megbízottjai"},
        {"source": "Zhentarim", "target": "Party", "label": "Vadásznak rájuk"},
        {"source": "Zhentarim", "target": "King", "label": "Beépültek"}
    ]

if "dm_notes" not in st.session_state:
    st.session_state.dm_notes = "Ide írhatod a titkos DM jegyzeteidet a kampányhoz..."

# ==========================================
# 2. FELÜLET KIALAKÍTÁSA (Fülek)
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["🕸️ Kapcsolati Háló", "🛡️ Frakciók és Hírnév", "📅 Naptár és Időjárás", "📝 DM Jegyzetek"])

# --- FÜL 1: KAPCSOLATI HÁLÓ (Agraph) ---
with tab1:
    st.subheader("Intrikák és Kapcsolatok")
    st.markdown("Vizuális áttekintés a kampányod szereplőiről és a köztük lévő viszonyokról. A csomópontok mozgathatóak!")
    
    col_graph, col_add = st.columns([3, 1])
    
    with col_graph:
        # Node-ok és Edge-ek generálása a session_state alapján
        nodes = [Node(id=n["id"], label=n["label"], size=n["size"], color=n["color"], shape=n["shape"]) for n in st.session_state.graph_nodes]
        edges = [Edge(source=e["source"], target=e["target"], label=e["label"]) for e in st.session_state.graph_edges]
        
        # Gráf beállításai
        config = Config(
            width="100%",
            height=500,
            directed=True, # Nyilas kapcsolatok
            physics=True,  # Interaktív fizika
            hierarchical=False,
            nodeHighlightBehavior=True,
            highlightColor="#F7A7A6",
            collapsible=False
        )
        
        # Gráf kirajzolása
        return_value = agraph(nodes=nodes, edges=edges, config=config)
        
    with col_add:
        st.markdown("### Új Kapcsolat")
        node_ids = [n["id"] for n in st.session_state.graph_nodes]
        
        source = st.selectbox("Honnan (Kiből indul):", node_ids)
        target = st.selectbox("Hová (Kire mutat):", node_ids)
        relation = st.text_input("Kapcsolat jellege (pl. Zsarolja):")
        
        if st.button("Hozzáadás", use_container_width=True):
            if source != target and relation:
                st.session_state.graph_edges.append({"source": source, "target": target, "label": relation})
                st.rerun()
            else:
                st.warning("Érvénytelen kapcsolat!")

# --- FÜL 2: FRAKCIÓK ---
with tab2:
    st.subheader("Frakciók és Hírnév (Reputation System)")
    st.markdown("A táblázat szerkeszthető! Kövesd nyomon, hogy a játékosok hol állnak az egyes csoportoknál.")
    
    edited_factions = st.data_editor(
        st.session_state.factions,
        num_rows="dynamic",
        use_container_width=True,
        key="faction_editor"
    )
    st.session_state.factions = edited_factions

# --- FÜL 3: NAPTÁR ÉS IDŐJÁRÁS ---
with tab3:
    st.subheader("Időmúlás és Időjárás")
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.session_state.calendar["nap"] = st.number_input("Eltelt Napok", value=st.session_state.calendar["nap"], step=1)
    with c2:
        st.session_state.calendar["honap"] = st.selectbox("Évszak / Hónap", ["Tavasz", "Nyár", "Ősz", "Tél"], index=["Tavasz", "Nyár", "Ősz", "Tél"].index(st.session_state.calendar["honap"]))
    with c3:
        st.session_state.calendar["idojaras"] = st.text_input("Aktuális Időjárás", value=st.session_state.calendar["idojaras"])
    with c4:
        st.session_state.calendar["ido"] = st.time_input("Pontos idő", value=pd.to_datetime(st.session_state.calendar["ido"]).time())

    st.info(f"⏳ **Aktuális Kampány Idő:** {st.session_state.calendar['nap']}. nap, {st.session_state.calendar['honap']} - {st.session_state.calendar['idojaras']} ({st.session_state.calendar['ido']})")
    
    if st.button("🎲 Véletlen Időjárás Generálása (Egyszerű)"):
        weather_options = ["Tiszta égbolt", "Enyhe eső", "Hatalmas vihar", "Ködös, sűrű pára", "Nyomasztó hőség", "Metsző hideg szél"]
        import random
        st.session_state.calendar["idojaras"] = random.choice(weather_options)
        st.rerun()

# --- FÜL 4: JEGYZETEK ---
with tab4:
    st.subheader("Kalandmesteri Jegyzetek")
    st.session_state.dm_notes = st.text_area("Wiki / Titkok / Emlékeztetők", value=st.session_state.dm_notes, height=300)
    st.caption("Ezek az adatok a munkamenet (Session) végéig megmaradnak. Később ide beköthetünk egy Mentés fájlba (JSON/SQLite) gombot is.")

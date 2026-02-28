import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image

st.set_page_config(page_title="VTT Map", page_icon="🗺️", layout="wide")
st.title("🗺️ VTT Térkép és Háború Ködje")

st.markdown("Töltsd fel a harctéri térképet (akár nagy felbontásút is!), majd használd a bal oldali eszközöket a letakarásához vagy a területre ható (AoE) varázslatok berajzolásához.")

uploaded_file = st.file_uploader("Válaszd ki a térképet", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    with st.spinner("Térkép varázslása az asztalra..."):
        try:
            # Kép betöltése és RGB konverzió (a fekete hátterek ellen)
            bg_image = Image.open(uploaded_file).convert("RGB")
            
            # 1. Kiszámoljuk a pontos méretarányokat
            orig_width, orig_height = bg_image.size
            aspect_ratio = orig_height / orig_width
            
            canvas_width = 800  # Fix asztal szélesség
            canvas_height = int(canvas_width * aspect_ratio)
            
            # 2. SENIOR TRÜKK: Hajszálpontosan a vászonra méretezzük a képet!
            # Így 0 memóriapazarlás lesz, a feltöltés pedig villámgyors.
            bg_image = bg_image.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS)
            
        except Exception as e:
            st.error(f"❌ Hiba a kép betöltésekor: {str(e)}")
            st.stop()

    # ==========================================
    # 2. VTT ESZKÖZTÁR (Oldalsáv)
    # ==========================================
    st.sidebar.header("🛠️ VTT Eszköztár")
    
    drawing_mode = st.sidebar.selectbox(
        "Rajzolási Mód",
        ("rect", "polygon", "transform", "freedraw", "line", "circle"),
        format_func=lambda x: {
            "rect": "⬛ Szoba letakarása (Téglalap)",
            "polygon": "🛑 Barlang letakarása (Poligon)",
            "transform": "🖐️ Felfedés / Mozgatás (Kijelölés)",
            "freedraw": "✏️ Szabadkézi rajz (Jegyzet)",
            "line": "📏 Vonal (Távolság/Fal)",
            "circle": "🔥 AoE Sablon (Kör/Tűzgolyó)"
        }[x]
    )

    stroke_width = st.sidebar.slider("Vonalvastagság", 1, 25, 3)
    
    if drawing_mode in ["rect", "polygon"]:
        st.sidebar.info("Tipp: Rajzolj formákat a szobák letakarásához (Fog of War).")
        stroke_color = "#000000"
        fill_color = "rgba(0, 0, 0, 1.0)"
    elif drawing_mode == "circle":
        st.sidebar.info("Tipp: AoE varázslat. Félig átlátszó piros kör.")
        stroke_color = "#FF0000"
        fill_color = "rgba(255, 0, 0, 0.3)"
    elif drawing_mode == "transform":
        st.sidebar.info("Tipp: Kattints egy letakart szobára, majd nyomd meg a **Delete / Backspace** gombot a billentyűzeten a felfedéshez!")
        stroke_color = "#000000"
        fill_color = "rgba(0, 0, 0, 0)"
    else:
        st.sidebar.info("Tipp: Szabadkézi rajz vagy vonal meghúzása a térképen.")
        stroke_color = st.sidebar.color_picker("Vonal Színe", "#FFFF00")
        fill_color = "rgba(0, 0, 0, 0)"

    # ==========================================
    # 3. INTERAKTÍV VÁSZON (Canvas)
    # ==========================================
    st.markdown("### 🎲 Asztal")
    
    # 3. SENIOR TRÜKK: Dinamikus kulcs a fájlnévből!
    # Így a rendszer nem használja az előző, elrontott fehér "cache-t".
    canvas_key = f"vtt_{uploaded_file.name}"
    
    canvas_result = st_canvas(
        fill_color=fill_color,
        stroke_width=stroke_width,
        stroke_color=stroke_color,
        background_image=bg_image, 
        update_streamlit=True,
        height=canvas_height,
        width=canvas_width,
        drawing_mode=drawing_mode,
        key=canvas_key,
    )

else:
    st.info("Kérlek, tölts fel egy térképet a kezdéshez! 🗺️")

import os
import shutil
import uuid
import requests
from typing import List, Optional
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq

# Környezeti változók betöltése (.env fájlból)
load_dotenv()

# ==========================================
# ALKALMAZÁS INICIALIZÁLÁSA
# ==========================================
app = FastAPI(
    title="D&D Kalandmester API",
    description="Backend motor VTT-hez, AI-hoz, Kaland Kódexhez és Encounter Trackerhez",
    version="1.0.0"
)

# CORS (Frontend engedélyezése)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Groq kliens felébresztése
api_key = os.getenv("GROQ_API_KEY")
if api_key:
    groq_client = Groq(api_key=api_key)
else:
    print("❌ HIBA: Nem találom a GROQ_API_KEY-t a .env fájlban!")

# ==========================================
# MAPPÁK ÉS FÁJLOK BEÁLLÍTÁSA
# ==========================================
# Térképek (VTT)
UPLOAD_DIR = "uploads/maps"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/maps", StaticFiles(directory=UPLOAD_DIR), name="maps")

# Kaland Kódexe (Lore Vault)
LORE_DIR = "uploads/lore"
os.makedirs(LORE_DIR, exist_ok=True)
LORE_FILE = os.path.join(LORE_DIR, "campaign_lore.txt")

if not os.path.exists(LORE_FILE):
    with open(LORE_FILE, "w", encoding="utf-8") as f:
        f.write("A kaland kódexe. Itt gyűlnek a Kalandmester titkos jegyzetei:\n\n")

# Encounter memória (Jelenleg futó harc)
active_encounter = []

# ==========================================
# ADATMODELLEK (Kommunikáció a React-tel)
# ==========================================
class PromptRequest(BaseModel):
    prompt: str

class AIResponse(BaseModel):
    result: str

class Combatant(BaseModel):
    id: str
    name: str
    is_player: bool
    hp: int
    max_hp: int
    ac: int
    initiative: int = 0

# ==========================================
# 1. ALAP VÉGPONTOK ÉS VTT TÉRKÉP
# ==========================================
@app.get("/")
async def root():
    return {"message": "A D&D Kalandmester Backend aktív és bevetésre kész. 🎲"}

@app.post("/api/vtt/upload-map")
async def upload_map(file: UploadFile = File(...)):
    """Térkép feltöltése a virtuális asztalra."""
    try:
        file_extension = file.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return {
            "message": "Térkép feltöltve!", 
            "url": f"http://localhost:8000/maps/{unique_filename}", 
            "filename": unique_filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 2. KALAND KÓDEXE ÉS LORE VÉGPONTOK (RAG)
# ==========================================
@app.post("/api/lore/upload")
async def upload_lore(file: UploadFile = File(...)):
    """Szöveges fájl (titkos jegyzet) hozzáadása a Kódexhez."""
    try:
        content = await file.read()
        text_content = content.decode("utf-8")
        with open(LORE_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n--- Új bejegyzés: {file.filename} ---\n")
            f.write(text_content)
            f.write("\n")
        return {"message": f"'{file.filename}' sikeresen hozzáadva a Kódexhez!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hiba a Lore olvasásakor: {str(e)}")

@app.post("/api/ai/lore-master", response_model=AIResponse)
async def ask_lore_master(req: PromptRequest):
    """AI, ami a saját feltöltött jegyzeteid (Kódex) alapján válaszol."""
    try:
        current_lore = ""
        if os.path.exists(LORE_FILE):
            with open(LORE_FILE, "r", encoding="utf-8") as f:
                current_lore = f.read()
                
        system_prompt = f"""Te egy D&D Kalandmester asszisztens vagy. A válaszaidat KIZÁRÓLAG az alábbi Kódexre alapozd:
        
        {current_lore}
        
        Ha a kérdésre nincs válasz a Kódexben, találd ki logikusan a világ hangulatához illően. Magyarul válaszolj!"""
        
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": req.prompt}],
            model="llama-3.3-70b-versatile", temperature=0.6)
        return AIResponse(result=chat_completion.choices[0].message.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 3. ÁLTALÁNOS AI ASSZISZTENS VÉGPONTOK
# ==========================================
@app.post("/api/ai/rules-lawyer", response_model=AIResponse)
async def ask_rules_lawyer(req: PromptRequest):
    """5e Szabálybíró."""
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "system", "content": "Te egy profi D&D 5e Szabálybíró vagy. Légy pontos és hivatkozz a szabályokra magyarul."}, 
                      {"role": "user", "content": req.prompt}],
            model="llama-3.3-70b-versatile", temperature=0.3)
        return AIResponse(result=chat_completion.choices[0].message.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/npc-generator", response_model=AIResponse)
async def generate_npc(req: PromptRequest):
    """NJK (Karakter) Generátor."""
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "system", "content": "Te egy kreatív D&D 5e Kalandmester vagy. Készíts izgalmas NJK-t névvel, fajjal, kaszttal, titokkal és jellemmel. Magyarul válaszolj."}, 
                      {"role": "user", "content": req.prompt}],
            model="llama-3.3-70b-versatile", temperature=0.8)
        return AIResponse(result=chat_completion.choices[0].message.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/location-generator", response_model=AIResponse)
async def generate_location(req: PromptRequest):
    """Helyszín és hangulat leíró (Read-aloud text)."""
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "system", "content": "Te egy profi fantasy író vagy. Generálj magával ragadó helyszínleírást a játékosoknak, bevonva az érzékszerveket. Magyarul válaszolj."}, 
                      {"role": "user", "content": req.prompt}],
            model="llama-3.3-70b-versatile", temperature=0.7)
        return AIResponse(result=chat_completion.choices[0].message.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/improvise", response_model=AIResponse)
async def improvise_scenario(req: PromptRequest):
    """Pánikgomb: 3 kreatív ötlet váratlan helyzetekre."""
    try:
        current_lore = ""
        if os.path.exists(LORE_FILE):
            with open(LORE_FILE, "r", encoding="utf-8") as f:
                current_lore = f.read()
                
        system_prompt = f"""A kampány háttere: {current_lore}
        Adj a mesélőnek PONTOSAN 3 KÜLÖNBÖZŐ, kreatív ötletet a kérdésére. Legyen köztük vicces, komoly, és egy váratlan fordulat is. Vázlatpontokban, magyarul!"""
        
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": req.prompt}],
            model="llama-3.3-70b-versatile", temperature=0.8)
        return AIResponse(result=chat_completion.choices[0].message.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 4. ENCOUNTER TRACKER (Harc követése)
# ==========================================
@app.get("/api/encounter/search-monster/{monster_index}")
async def search_monster(monster_index: str):
    """Szörny statisztikák letöltése a hivatalos SRD adatbázisból."""
    try:
        url = f"https://www.dnd5eapi.co/api/monsters/{monster_index.lower()}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            ac = data["armor_class"][0]["value"] if "armor_class" in data and len(data["armor_class"]) > 0 else 10
            return {"name": data["name"], "max_hp": data["hit_points"], "ac": ac, "dexterity": data["dexterity"]}
        else:
            raise HTTPException(status_code=404, detail="Szörny nem található az SRD-ben.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/encounter/add")
async def add_combatant(combatant: Combatant):
    """Karakter/Szörny hozzáadása a harchoz."""
    active_encounter.append(combatant.dict())
    return {"message": f"{combatant.name} csatlakozott a harchoz!"}

@app.get("/api/encounter/current")
async def get_encounter():
    """Az aktív harc résztvevőinek listája (Kezdeményezés szerint rendezve)."""
    sorted_encounter = sorted(active_encounter, key=lambda x: x["initiative"], reverse=True)
    return {"combatants": sorted_encounter}

@app.delete("/api/encounter/clear")
async def clear_encounter():
    """A harc befejezése (asztal törlése)."""
    active_encounter.clear()
    return {"message": "A harc véget ért, az asztal letakarítva!"}

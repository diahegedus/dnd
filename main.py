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

load_dotenv()

app = FastAPI(
    title="D&D Kalandmester API",
    description="Backend motor VTT-hez, AI-hoz és Kaland Kódexhez (Lore Vault)",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key = os.getenv("GROQ_API_KEY")
if api_key:
    groq_client = Groq(api_key=api_key)

# ==========================================
# 0. MAPPÁK ÉS FÁJLOK BEÁLLÍTÁSA
# ==========================================
# Térképek mappája
UPLOAD_DIR = "uploads/maps"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/maps", StaticFiles(directory=UPLOAD_DIR), name="maps")

# Kaland Kódexe (Lore Vault) beállítása
LORE_DIR = "uploads/lore"
os.makedirs(LORE_DIR, exist_ok=True)
LORE_FILE = os.path.join(LORE_DIR, "campaign_lore.txt")

# Ha még nincs Kódex fájl, létrehozzuk üresen
if not os.path.exists(LORE_FILE):
    with open(LORE_FILE, "w", encoding="utf-8") as f:
        f.write("A kaland kódexe. Itt gyűlnek a Kalandmester titkos jegyzetei:\n\n")

# Encounter memória
active_encounter = []

# ==========================================
# 1. ADATMODELLEK
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
# 2. ALAP VÉGPONTOK ÉS TÉRKÉP
# ==========================================
@app.get("/")
async def root():
    return {"message": "A D&D Kalandmester Backend (Lore Vaulttal) aktív. 🎲"}

@app.post("/api/vtt/upload-map")
async def upload_map(file: UploadFile = File(...)):
    try:
        file_extension = file.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"message": "Térkép feltöltve!", "url": f"http://localhost:8000/maps/{unique_filename}", "filename": unique_filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 3. ÚJ: KALAND KÓDEXE ÉS LORE MASTER AI
# ==========================================
@app.post("/api/lore/upload")
async def upload_lore(file: UploadFile = File(...)):
    """Ide töltheted fel a TXT formátumú jegyzeteidet a kampányról."""
    try:
        content = await file.read()
        text_content = content.decode("utf-8")
        
        # Hozzáírjuk a feltöltött szöveget a közös Kódexhez
        with open(LORE_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n--- Új bejegyzés: {file.filename} ---\n")
            f.write(text_content)
            f.write("\n")
            
        return {"message": f"'{file.filename}' sikeresen hozzáadva a Kódexhez! Az AI mostantól ismeri ezt a történetet."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hiba a Lore olvasásakor: {str(e)}")

@app.post("/api/ai/lore-master", response_model=AIResponse)
async def ask_lore_master(req: PromptRequest):
    """Ez az AI végpont a SAJÁT jegyzeteid alapján válaszol."""
    try:
        # Beolvassuk a jelenlegi teljes Kódexet
        with open(LORE_FILE, "r", encoding="utf-8") as f:
            current_lore = f.read()
            
        system_prompt = f"""Te egy D&D Kalandmester asszisztens vagy. A válaszaidat KIZÁRÓLAG az alábbi Kódexre (Lore) alapozd:
        
        --- KALAND KÓDEXE ---
        {current_lore}
        ---------------------
        
        Ha a játékos/kalandmester kérdésére nincs válasz a Kódexben, találd ki logikusan a világ hangulatához illően, vagy mondd el, hogy ez még rejtély. Magyarul válaszolj!"""
        
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": req.prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.6,
        )
        return AIResponse(result=chat_completion.choices[0].message.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 4. KORÁBBI AI ÉS ENCOUNTER VÉGPONTOK (Rövidítve a kód tisztaságáért)
# ==========================================
@app.post("/api/ai/rules-lawyer", response_model=AIResponse)
async def ask_rules_lawyer(req: PromptRequest):
    chat_completion = groq_client.chat.completions.create(
        messages=[{"role": "system", "content": "Te egy D&D 5e Szabálybíró vagy."}, {"role": "user", "content": req.prompt}],
        model="llama-3.3-70b-versatile", temperature=0.3)
    return AIResponse(result=chat_completion.choices[0].message.content)

@app.get("/api/encounter/search-monster/{monster_index}")
async def search_monster(monster_index: str):
    url = f"https://www.dnd5eapi.co/api/monsters/{monster_index.lower()}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        ac = data["armor_class"][0]["value"] if "armor_class" in data and len(data["armor_class"]) > 0 else 10
        return {"name": data["name"], "max_hp": data["hit_points"], "ac": ac, "dexterity": data["dexterity"]}
    raise HTTPException(status_code=404, detail="Szörny nem található.")

@app.post("/api/encounter/add")
async def add_combatant(combatant: Combatant):
    active_encounter.append(combatant.dict())
    return {"message": f"{combatant.name} csatlakozott a harchoz!"}

@app.get("/api/encounter/current")
async def get_encounter():
    return {"combatants": sorted(active_encounter, key=lambda x: x["initiative"], reverse=True)}

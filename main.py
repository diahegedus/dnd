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
    description="Backend motor a React VTT, AI és Encounter Trackerhez",
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

UPLOAD_DIR = "uploads/maps"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/maps", StaticFiles(directory=UPLOAD_DIR), name="maps")

# ==========================================
# 1. ENCOUNTER ÁLLAPOT (Memóriában tárolt "Adatbázis")
# ==========================================
# Ez a lista fogja tárolni, hogy kik vannak épp harcban az asztalon.
active_encounter = []

# ==========================================
# 2. ADATMODELLEK
# ==========================================
class PromptRequest(BaseModel):
    prompt: str

class AIResponse(BaseModel):
    result: str

# ÚJ: Harctéri résztvevő modellje
class Combatant(BaseModel):
    id: str
    name: str
    is_player: bool
    hp: int
    max_hp: int
    ac: int
    initiative: int = 0

# ==========================================
# 3. ALAP ÉS AI VÉGPONTOK (A korábbiak)
# ==========================================
@app.get("/")
async def root():
    return {"message": "A D&D Kalandmester Backend aktív. 🎲"}

@app.post("/api/ai/rules-lawyer", response_model=AIResponse)
async def ask_rules_lawyer(req: PromptRequest):
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Te egy profi D&D 5e Szabálybíró vagy. Légy pontos és hivatkozz a szabályokra magyarul."},
                {"role": "user", "content": req.prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
        )
        return AIResponse(result=chat_completion.choices[0].message.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/vtt/upload-map")
async def upload_map(file: UploadFile = File(...)):
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
# 4. ÚJ: ENCOUNTER TRACKER VÉGPONTOK
# ==========================================

# 4.1 Szörny adatainak behúzása a D&D 5e SRD-ből (mint a D&D Beyond)
@app.get("/api/encounter/search-monster/{monster_index}")
async def search_monster(monster_index: str):
    """
    Kikeresi egy szörny alapadatait az internetes D&D adatbázisból.
    Példa bemenet: 'goblin', 'adult-red-dragon', 'bandit'
    """
    try:
        url = f"https://www.dnd5eapi.co/api/monsters/{monster_index.lower()}"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            # Kinyerjük az AC (Armor Class) értéket
            ac = 10
            if "armor_class" in data and len(data["armor_class"]) > 0:
                ac = data["armor_class"][0]["value"]
                
            return {
                "name": data["name"],
                "max_hp": data["hit_points"],
                "ac": ac,
                "dexterity": data["dexterity"], # Hasznos a Kezdeményezés dobáshoz!
                "type": data["type"],
                "size": data["size"]
            }
        else:
            raise HTTPException(status_code=404, detail="Szörny nem található az SRD-ben.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 4.2 Harcos hozzáadása az asztalhoz
@app.post("/api/encounter/add")
async def add_combatant(combatant: Combatant):
    active_encounter.append(combatant.dict())
    return {"message": f"{combatant.name} csatlakozott a harchoz!"}

# 4.3 Jelenlegi harcállás lekérése (Kezdeményezés szerint rendezve!)
@app.get("/api/encounter/current")
async def get_encounter():
    # Rendezzük a listát csökkenő sorrendbe az initiative (kezdeményezés) alapján
    sorted_encounter = sorted(active_encounter, key=lambda x: x["initiative"], reverse=True)
    return {"combatants": sorted_encounter}

# 4.4 Harc vége (Asztal letakarítása)
@app.delete("/api/encounter/clear")
async def clear_encounter():
    active_encounter.clear()
    return {"message": "A harc véget ért, az asztal letakarítva!"}

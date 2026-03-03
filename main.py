import os
import shutil
import uuid
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq

# Környezeti változók betöltése (.env)
load_dotenv()

app = FastAPI(
    title="D&D Kalandmester API",
    description="Backend motor a React VTT és AI Asszisztenshez",
    version="1.0.0"
)

# CORS beállítások (a React frontendhez)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Groq kliens inicializálása
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("❌ HIBA: Nem találom a GROQ_API_KEY-t a .env fájlban!")
groq_client = Groq(api_key=api_key)

# ==========================================
# 0. TÉRKÉPEK (STATIKUS FÁJLOK) BEÁLLÍTÁSA
# ==========================================
UPLOAD_DIR = "uploads/maps"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/maps", StaticFiles(directory=UPLOAD_DIR), name="maps")

# ==========================================
# 1. ADATMODELLEK (Kommunikáció a React-tel)
# ==========================================
class PromptRequest(BaseModel):
    prompt: str

class AIResponse(BaseModel):
    result: str

# ==========================================
# 2. ALAP VÉGPONTOK
# ==========================================
@app.get("/")
async def root():
    return {"message": "A D&D Kalandmester Backend aktív. 🎲"}

# ==========================================
# 3. AI VÉGPONTOK (Groq)
# ==========================================
# 3.1 Szabálybíró
@app.post("/api/ai/rules-lawyer", response_model=AIResponse)
async def ask_rules_lawyer(req: PromptRequest):
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Te egy profi D&D 5e Szabálybíró vagy. Légy pontos és hivatkozz a szabályokra magyarul. Ne kalandozz el, csak a szabályokat tisztázd."},
                {"role": "user", "content": req.prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3, # Alacsony kreativitás, szigorú szabályok
        )
        return AIResponse(result=chat_completion.choices[0].message.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 3.2 NJK (Nem Játékos Karakter) Generátor
@app.post("/api/ai/npc-generator", response_model=AIResponse)
async def generate_npc(req: PromptRequest):
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Te egy kreatív D&D 5e Kalandmester vagy. A feladatod egy izgalmas, egyedi NJK (Karakter) kidolgozása a megadott leírás alapján. Írj le egy nevet, fajt, kasztot/foglalkozást, egy titkot, és a viselkedését. Magyarul válaszolj."},
                {"role": "user", "content": req.prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.8, # Magasabb kreativitás
        )
        return AIResponse(result=chat_completion.choices[0].message.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 3.3 Helyszín és Hangulat Leírás
@app.post("/api/ai/location-generator", response_model=AIResponse)
async def generate_location(req: PromptRequest):
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Te egy profi fantasy író és D&D Kalandmester vagy. A feladatod egy magával ragadó, hangulatos helyszínleírás (read-aloud text) generálása a játékosok számára, amely bevonja az érzékszerveket (látvány, hang, szag). Magyarul válaszolj."},
                {"role": "user", "content": req.prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
        )
        return AIResponse(result=chat_completion.choices[0].message.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 4. VTT (Virtuális Asztal) VÉGPONTOK
# ==========================================
@app.post("/api/vtt/upload-map")
async def upload_map(file: UploadFile = File(...)):
    try:
        file_extension = file.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        image_url = f"http://localhost:8000/maps/{unique_filename}"
        
        return {
            "message": "Térkép sikeresen feltöltve!", 
            "url": image_url,
            "filename": unique_filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hiba a kép feldolgozásakor: {str(e)}")

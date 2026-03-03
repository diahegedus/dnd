import os
import shutil
import uuid
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq

# Környezeti változók betöltése
load_dotenv()

app = FastAPI(
    title="D&D Kalandmester API",
    description="Backend motor a React VTT és AI Asszisztenshez",
    version="1.0.0"
)

# CORS beállítások
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
# Létrehozzuk a mappát, ahova a térképek mentődnek
UPLOAD_DIR = "uploads/maps"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# "Felcsatoljuk" a mappát a szerverre. 
# Így a React egy sima URL-lel (pl. http://localhost:8000/maps/kep.jpg) eléri a térképet!
app.mount("/maps", StaticFiles(directory=UPLOAD_DIR), name="maps")

# ==========================================
# 1. ADATMODELLEK
# ==========================================
class RuleQuestion(BaseModel):
    question: str

class RuleAnswer(BaseModel):
    answer: str

# ==========================================
# 2. VÉGPONTOK (API Routes)
# ==========================================
@app.get("/")
async def root():
    return {"message": "A D&D Kalandmester Backend aktív. 🎲"}

# --- AI Szabálybíró ---
@app.post("/api/rules-lawyer", response_model=RuleAnswer)
async def ask_rules_lawyer(req: RuleQuestion):
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Te egy profi D&D 5e Szabálybíró vagy. Légy pontos és hivatkozz a szabályokra magyarul."},
                {"role": "user", "content": req.question}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
        )
        return RuleAnswer(answer=chat_completion.choices[0].message.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- ÚJ: VTT Térkép Feltöltése ---
@app.post("/api/vtt/upload-map")
async def upload_map(file: UploadFile = File(...)):
    try:
        # Generálunk egy egyedi azonosítót a fájlnak (hogy a "tavern.jpg" ne írja felül a másik "tavern.jpg"-t)
        file_extension = file.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        # Lementjük a képet a szerver SSD/HDD-jére (gyors és memóriabarát)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Visszaküldjük a Reactnek a pontos linket, ahonnan betöltheti a vászonba
        image_url = f"http://localhost:8000/maps/{unique_filename}"
        
        return {
            "message": "Térkép sikeresen feltöltve az asztalra!", 
            "url": image_url,
            "filename": unique_filename
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hiba a kép feldolgozásakor: {str(e)}")

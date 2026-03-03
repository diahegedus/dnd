import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq

# Környezeti változók betöltése a .env fájlból
load_dotenv()

# Inicializáljuk a FastAPI alkalmazást
app = FastAPI(
    title="D&D Kalandmester API",
    description="Backend motor a React VTT és AI Asszisztenshez",
    version="1.0.0"
)

# CORS beállítások a React miatt
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Groq kliens felébresztése
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    print("❌ HIBA: Nem találom a GROQ_API_KEY-t a .env fájlban!")
groq_client = Groq(api_key=api_key)

# ==========================================
# 1. ADATMODELLEK (Mit vár és mit küld a szerver)
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
    return {"message": "Üdvözöllek a D&D Kalandmester Backendjén! A szerver aktív. 🎲"}

@app.get("/health")
async def health_check():
    return {"status": "ok", "hp": "MAX"}

# ÚJ VÉGPONT: AI Szabálybíró
@app.post("/api/rules-lawyer", response_model=RuleAnswer)
async def ask_rules_lawyer(req: RuleQuestion):
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "Te egy profi D&D 5e Szabálybíró (Rules Lawyer) vagy. A válaszaid magyar nyelven legyenek pontosak, lényegretörőek, és hivatkozz a hivatalos szabályokra."
                },
                {
                    "role": "user",
                    "content": req.question
                }
            ],
            model="llama-3.3-70b-versatile", # Az új, aktív modell
            temperature=0.3, # Alacsony érték, hogy ne találjon ki hülyeségeket, csak a szabályt mondja
        )
        
        reply = chat_completion.choices[0].message.content
        return RuleAnswer(answer=reply)
        
    except Exception as e:
        # Ha a Groq szerverével baj van, szépen továbbítjuk a hibát a Reactnek
        raise HTTPException(status_code=500, detail=str(e))

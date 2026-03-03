from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Inicializáljuk a FastAPI alkalmazást
app = FastAPI(
    title="D&D Kalandmester API",
    description="Backend motor a React VTT és AI Asszisztenshez",
    version="1.0.0"
)

# CORS beállítások (Hogy a React frontend gond nélkül tudjon csatlakozni)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Fejlesztés alatt mindent engedünk. Később ide kerül a React app pontos URL-je.
    allow_credentials=True,
    allow_methods=["*"],  # GET, POST, PUT, DELETE engedélyezése
    allow_headers=["*"],
)

# Egy egyszerű "Életjel" (Health Check) végpont
@app.get("/")
async def root():
    return {"message": "Üdvözöllek a D&D Kalandmester Backendjén! A szerver aktív. 🎲"}

@app.get("/health")
async def health_check():
    return {"status": "ok", "hp": "MAX"}

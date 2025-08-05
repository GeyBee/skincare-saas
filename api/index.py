from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import json
from datetime import datetime

app = FastAPI(title="SkinCare SaaS API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage temporaire
users_db = {}
profiles_db = {}

# Modèles
class UserRegister(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str

class SkinProfile(BaseModel):
    skin_type: str
    main_concerns: List[str]
    stress_level: int

@app.get("/")
def hello():
    return {"message": "Hello ! Ton API SkinCare fonctionne ! 🎉", "status": "OK"}

@app.post("/auth/register")
def register(user: UserRegister):
    if user.email in users_db:
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    
    users_db[user.email] = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "password": user.password,  # En production, il faut hasher !
        "created_at": datetime.now().isoformat()
    }
    
    return {
        "message": "Inscription réussie !",
        "user": {"email": user.email, "name": f"{user.first_name} {user.last_name}"}
    }

@app.post("/profile/skin")
def create_skin_profile(profile: SkinProfile, user_email: str = "demo@example.com"):
    profiles_db[user_email] = {
        "skin_type": profile.skin_type,
        "main_concerns": profile.main_concerns,
        "stress_level": profile.stress_level,
        "created_at": datetime.now().isoformat()
    }
    
    # Génération routine simple
    routine = {
        "morning": ["Nettoyant doux", "Hydratant", "SPF 30+"],
        "evening": ["Démaquillant", "Nettoyant", "Crème de nuit"]
    }
    
    if "acné" in profile.main_concerns:
        routine["evening"].insert(2, "Sérum anti-acné")
    
    return {
        "message": "Profil créé et routine générée !",
        "routine": routine,
        "skin_analysis": f"Peau {profile.skin_type} avec préoccupations: {', '.join(profile.main_concerns)}"
    }
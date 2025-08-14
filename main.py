from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
import bcrypt
import jwt
from datetime import datetime, timedelta
import json
import os
import random

# === IA FUNCTIONS ===
def analyze_skin_progress(checkins: List[Dict], photos: List[Dict]) -> Dict:
    """Analyse intelligente des progrès de la peau"""
    if not checkins:
        return {"trend": "insufficient_data", "confidence": 0}
    
    recent_checkins = sorted(checkins, key=lambda x: x["created_at"])[-7:]
    old_checkins = sorted(checkins, key=lambda x: x["created_at"])[:-7] if len(checkins) > 7 else []
    
    if not old_checkins:
        return {"trend": "not_enough_data", "confidence": 30}
    
    recent_avg = sum(c["skin_condition"] for c in recent_checkins) / len(recent_checkins)
    old_avg = sum(c["skin_condition"] for c in old_checkins) / len(old_checkins)
    
    improvement = recent_avg - old_avg
    
    if improvement > 1:
        trend = "significant_improvement"
        confidence = min(90, 70 + len(checkins) * 2)
    elif improvement > 0.3:
        trend = "moderate_improvement"
        confidence = min(80, 60 + len(checkins) * 2)
    elif improvement > -0.3:
        trend = "stable"
        confidence = min(75, 50 + len(checkins) * 2)
    else:
        trend = "declining"
        confidence = min(85, 65 + len(checkins) * 2)
    
    return {
        "trend": trend,
        "improvement_score": round(improvement, 2),
        "confidence": confidence,
        "recent_average": round(recent_avg, 1),
        "previous_average": round(old_avg, 1),
        "total_data_points": len(checkins),
        "photo_count": len(photos)
    }

def generate_ai_recommendations(profile: Dict, checkins: List[Dict], photos: List[Dict]) -> List[Dict]:
    """Génère des recommandations IA personnalisées"""
    recommendations = []
    
    skin_type = profile.get("skin_type", "normale")
    concerns = profile.get("main_concerns", [])
    stress_level = profile.get("stress_level", 5)
    
    products_db = {
        "nettoyants": [
            {"name": "CeraVe Gel Moussant", "price": 12.90, "rating": 4.6, "skin_types": ["normale", "mixte", "grasse"]},
            {"name": "La Roche-Posay Toleriane", "price": 15.50, "rating": 4.7, "skin_types": ["sensible", "sèche"]},
        ],
        "serums": [
            {"name": "The Ordinary Niacinamide 10%", "price": 7.50, "rating": 4.4, "concerns": ["acné", "pores dilatés"]},
            {"name": "Vichy Mineral 89", "price": 24.90, "rating": 4.5, "concerns": ["sécheresse", "sensibilité"]},
        ],
        "hydratants": [
            {"name": "Cetaphil Daily Moisturizer", "price": 11.90, "rating": 4.4, "skin_types": ["normale", "sèche"]},
            {"name": "Effaclar Mat La Roche-Posay", "price": 16.90, "rating": 4.3, "skin_types": ["grasse", "mixte"]},
        ]
    }
    
    for category, products in products_db.items():
        best_product = None
        best_score = 0
        
        for product in products:
            score = 0
            
            if "skin_types" in product and skin_type in product["skin_types"]:
                score += 40
            
            if "concerns" in product:
                matching_concerns = set(concerns) & set(product["concerns"])
                score += len(matching_concerns) * 30
            
            score += product["rating"] * 5
            
            if product["price"] < 15:
                score += 10
            elif product["price"] < 25:
                score += 5
            
            if score > best_score:
                best_score = score
                best_product = product
        
        if best_product:
            reasons = []
            if "skin_types" in best_product and skin_type in best_product["skin_types"]:
                reasons.append(f"Adapté aux peaux {skin_type}s")
            if "concerns" in best_product:
                matching = set(concerns) & set(best_product["concerns"])
                if matching:
                    reasons.append(f"Traite: {', '.join(matching)}")
            
            recommendations.append({
                "category": category.title(),
                "product": best_product,
                "match_score": min(100, int(best_score)),
                "reasons": reasons,
                "urgency": "high" if best_score > 80 else "medium" if best_score > 60 else "low"
            })
    
    if stress_level > 7:
        recommendations.append({
            "category": "Bien-être",
            "product": {
                "name": "Masque Apaisant Avène",
                "price": 13.90,
                "rating": 4.5,
                "description": "Masque anti-stress pour peaux sensibilisées."
            },
            "match_score": 85,
            "reasons": ["Niveau de stress élevé détecté"],
            "urgency": "medium"
        })
    
    return sorted(recommendations, key=lambda x: x["match_score"], reverse=True)

# Créer l'application
app = FastAPI(title="SkinCare SaaS API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
SECRET_KEY = "skincare-secret-key-2024"
ALGORITHM = "HS256"

# Stockage temporaire
users_db = {}
profiles_db = {}
checkins_db = {}
photos_db = {}

# Modèles Pydantic
class UserRegistration(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    age: int

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class SkinProfile(BaseModel):
    skin_type: str
    main_concerns: List[str]
    stress_level: int

class DailyCheckIn(BaseModel):
    skin_condition: int
    stress_level: int
    sleep_hours: int

# Fonctions utilitaires
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(days=30)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

# Routes API
@app.get("/", response_class=HTMLResponse)
async def home():
    html_content = """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SkinCare - Ton Coach Beauté Personnel</title>
        <style>
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                background: linear-gradient(135deg, #FF6B9D 0%, #C44569 100%);
                color: white;
                text-align: center;
                padding: 50px 20px;
                margin: 0;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
            }
            .container {
                max-width: 600px;
                width: 100%;
            }
            h1 { 
                font-size: 3.5em; 
                margin-bottom: 20px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
                animation: fadeIn 1s ease;
            }
            p { 
                font-size: 1.3em;
                margin-bottom: 40px;
                opacity: 0.95;
            }
            .buttons {
                display: flex;
                gap: 20px;
                justify-content: center;
                flex-wrap: wrap;
            }
            .btn {
                display: inline-block;
                padding: 15px 35px;
                background: white;
                color: #C44569;
                text-decoration: none;
                border-radius: 30px;
                font-weight: bold;
                font-size: 1.1em;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            }
            .btn:hover {
                transform: translateY(-3px);
                box-shadow: 0 6px 20px rgba(0,0,0,0.3);
                background: #f8f8f8;
            }
            .status {
                margin-top: 50px;
                padding: 20px;
                background: rgba(255,255,255,0.1);
                border-radius: 15px;
                backdrop-filter: blur(10px);
            }
            .status-item {
                display: inline-block;
                margin: 0 20px;
                font-size: 0.9em;
            }
            .status-item span {
                color: #90EE90;
                font-weight: bold;
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🌸 SkinCare App</h1>
            <p>Ton coach beauté personnel propulsé par l'IA</p>
            <div class="buttons">
                <a href="/docs" class="btn">📚 Explorer l'API</a>
                <a href="/health" class="btn">💚 Statut Système</a>
            </div>
            <div class="status">
                <div class="status-item">API: <span>✓ Opérationnel</span></div>
                <div class="status-item">Version: <span>1.0.0</span></div>
                <div class="status-item">IA: <span>✓ Activée</span></div>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/health")
def health_check():
    return {
        "status": "OK", 
        "app": "SkinCare API",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/auth/register")
def register(user_data: UserRegistration):
    if any(u["email"] == user_data.email for u in users_db.values()):
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    
    user_id = f"user_{len(users_db) + 1}"
    users_db[user_id] = {
        "id": user_id,
        "email": user_data.email,
        "password": hash_password(user_data.password),
        "first_name": user_data.first_name,
        "age": user_data.age,
        "created_at": datetime.utcnow().isoformat()
    }
    
    token = create_token(user_id)
    return {
        "message": "Compte créé avec succès !",
        "token": token,
        "user": {
            "id": user_id,
            "email": user_data.email,
            "first_name": user_data.first_name
        }
    }

@app.post("/auth/login")
def login(login_data: UserLogin):
    user = next((u for u in users_db.values() if u["email"] == login_data.email), None)
    if not user or not verify_password(login_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    
    token = create_token(user["id"])
    return {
        "message": "Connexion réussie !",
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "first_name": user["first_name"]
        }
    }

@app.post("/profile/skin")
def create_skin_profile(profile: SkinProfile):
    user_id = f"user_1"
    
    profiles_db[user_id] = {
        "user_id": user_id,
        "skin_type": profile.skin_type,
        "main_concerns": profile.main_concerns,
        "stress_level": profile.stress_level,
        "created_at": datetime.utcnow().isoformat()
    }
    
    return {
        "message": "Profil de peau créé avec succès !",
        "profile": profiles_db[user_id]
    }

@app.get("/profile/skin")
def get_skin_profile():
    user_id = "user_1"
    if user_id not in profiles_db:
        raise HTTPException(status_code=404, detail="Profil non trouvé")
    return profiles_db[user_id]

@app.post("/checkin")
def daily_checkin(checkin: DailyCheckIn):
    user_id = "user_1"
    today = datetime.utcnow().date().isoformat()
    checkin_id = f"{user_id}_{today}"
    
    checkins_db[checkin_id] = {
        "user_id": user_id,
        "date": today,
        "skin_condition": checkin.skin_condition,
        "stress_level": checkin.stress_level,
        "sleep_hours": checkin.sleep_hours,
        "created_at": datetime.utcnow().isoformat()
    }
    
    return {
        "message": "Check-in enregistré !",
        "checkin": checkins_db[checkin_id]
    }

@app.get("/checkin/history")
def get_checkin_history():
    user_id = "user_1"
    user_checkins = [c for c in checkins_db.values() if c["user_id"] == user_id]
    return {"checkins": user_checkins, "count": len(user_checkins)}

@app.post("/photos/upload")
async def upload_photo(file: UploadFile = File(...), photo_type: str = "progress"):
    user_id = "user_1"
    
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Le fichier doit être une image")
    
    photo_id = f"photo_{datetime.utcnow().timestamp()}_{random.randint(1000,9999)}"
    filename = f"{photo_id}_{file.filename}"
    
    photo_data = {
        "id": photo_id,
        "user_id": user_id,
        "filename": filename,
        "type": photo_type,
        "upload_date": datetime.utcnow().isoformat(),
        "size": 0
    }
    
    photos_db[photo_id] = photo_data
    
    return {
        "message": "Photo uploadée avec succès !",
        "photo_id": photo_id,
        "photo": photo_data
    }

@app.get("/photos/gallery")
async def get_photo_gallery():
    user_id = "user_1"
    user_photos = [photo for photo in photos_db.values() if photo["user_id"] == user_id]
    user_photos.sort(key=lambda x: x["upload_date"], reverse=True)
    
    return {
        "photos": user_photos,
        "count": len(user_photos)
    }

@app.delete("/photos/{photo_id}")
async def delete_photo(photo_id: str):
    if photo_id not in photos_db:
        raise HTTPException(status_code=404, detail="Photo non trouvée")
    
    deleted_photo = photos_db.pop(photo_id)
    return {"message": "Photo supprimée", "photo": deleted_photo}

@app.get("/analytics/progress")
async def get_progress_analytics():
    user_id = "user_1"
    
    user_checkins = [c for c in checkins_db.values() if c["user_id"] == user_id]
    user_photos = [p for p in photos_db.values() if p["user_id"] == user_id]
    
    if not user_checkins:
        return {"message": "Pas assez de données pour l'analyse"}
    
    skin_conditions = [c["skin_condition"] for c in user_checkins]
    stress_levels = [c["stress_level"] for c in user_checkins]
    
    analytics = {
        "total_checkins": len(user_checkins),
        "total_photos": len(user_photos),
        "avg_skin_condition": round(sum(skin_conditions) / len(skin_conditions), 1),
        "avg_stress_level": round(sum(stress_levels) / len(stress_levels), 1),
        "skin_trend": "amélioration" if len(skin_conditions) >= 2 and skin_conditions[-1] > skin_conditions[0] else "stable",
        "best_skin_day": max(skin_conditions) if skin_conditions else 0,
        "worst_skin_day": min(skin_conditions) if skin_conditions else 0,
        "consistency_score": round((len(user_checkins) / 30) * 100, 1)
    }
    
    return analytics

@app.get("/ai/recommendations")
async def get_ai_recommendations():
    user_id = "user_1"
    
    profile = profiles_db.get(user_id, {})
    checkins = [c for c in checkins_db.values() if c["user_id"] == user_id]
    photos = [p for p in photos_db.values() if p["user_id"] == user_id]
    
    if not profile:
        return {"message": "Créez d'abord votre profil de peau", "recommendations": []}
    
    recommendations = generate_ai_recommendations(profile, checkins, photos)
    progress = analyze_skin_progress(checkins, photos)
    
    return {
        "recommendations": recommendations,
        "skin_analysis": progress,
        "total_recommendations": len(recommendations),
        "generated_at": datetime.utcnow().isoformat()
    }
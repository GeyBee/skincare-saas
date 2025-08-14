from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
import bcrypt
import jwt
from datetime import datetime, timedelta
import json
import os
import uuid
import random

# === IA FUNCTIONS ===
def analyze_skin_progress(checkins: List[Dict], photos: List[Dict]) -> Dict:
    """Analyse intelligente des progrès de la peau"""
    if not checkins:
        return {"trend": "insufficient_data", "confidence": 0}
    
    # Analyser les tendances
    recent_checkins = sorted(checkins, key=lambda x: x["created_at"])[-7:]  # 7 derniers jours
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
    
    # Base de données produits
    products_db = {
        "nettoyants": [
            {"name": "CeraVe Gel Moussant", "price": 12.90, "rating": 4.6, "skin_types": ["normale", "mixte", "grasse"]},
            {"name": "La Roche-Posay Toleriane", "price": 15.50, "rating": 4.7, "skin_types": ["sensible", "sèche"]},
            {"name": "Neutrogena Ultra Gentle", "price": 8.99, "rating": 4.3, "skin_types": ["sensible", "normale"]},
        ],
        "serums": [
            {"name": "The Ordinary Niacinamide 10%", "price": 7.50, "rating": 4.4, "concerns": ["acné", "pores dilatés"]},
            {"name": "Vichy Mineral 89", "price": 24.90, "rating": 4.5, "concerns": ["sécheresse", "sensibilité"]},
            {"name": "Paula's Choice BHA 2%", "price": 33.00, "rating": 4.7, "concerns": ["acné", "points noirs"]},
        ],
        "hydratants": [
            {"name": "Cetaphil Daily Moisturizer", "price": 11.90, "rating": 4.4, "skin_types": ["normale", "sèche"]},
            {"name": "Effaclar Mat La Roche-Posay", "price": 16.90, "rating": 4.3, "skin_types": ["grasse", "mixte"]},
            {"name": "Toleriane Ultra Fluide", "price": 18.50, "rating": 4.6, "skin_types": ["sensible"]},
        ]
    }
    
    # Recommandations basées sur le type de peau
    for category, products in products_db.items():
        best_product = None
        best_score = 0
        
        for product in products:
            score = 0
            
            # Score basé sur le type de peau
            if "skin_types" in product and skin_type in product["skin_types"]:
                score += 40
            
            # Score basé sur les préoccupations
            if "concerns" in product:
                matching_concerns = set(concerns) & set(product["concerns"])
                score += len(matching_concerns) * 30
            
            # Score basé sur la note
            score += product["rating"] * 5
            
            # Score basé sur le prix
            if product["price"] < 15:
                score += 10
            elif product["price"] < 25:
                score += 5
            
            if score > best_score:
                best_score = score
                best_product = product
        
        if best_product:
            # Calculer la raison de la recommandation
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
    
    # Recommandations basées sur le stress
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
            "reasons": ["Niveau de stress élevé détecté", "Aide à calmer les inflammations"],
            "urgency": "medium"
        })
    
    return sorted(recommendations, key=lambda x: x["match_score"], reverse=True)

def predict_future_results(profile: Dict, checkins: List[Dict]) -> Dict:
    """Prédit les résultats futurs"""
    if len(checkins) < 3:
        return {"message": "Pas assez de données pour une prédiction fiable"}
    
    progress = analyze_skin_progress(checkins, [])
    current_avg = progress.get("recent_average", 5)
    trend = progress.get("improvement_score", 0)
    
    predictions = {}
    
    for weeks in [2, 4, 8, 12]:
        predicted_score = current_avg + (trend * weeks * 0.3)
        predicted_score = max(1, min(10, predicted_score))
        
        predictions[f"week_{weeks}"] = {
            "predicted_score": round(predicted_score, 1),
            "confidence": max(30, progress["confidence"] - (weeks * 5)),
            "description": get_prediction_description(predicted_score)
        }
    
    return {
        "current_score": current_avg,
        "trend_direction": "amélioration" if trend > 0 else "stable" if trend > -0.3 else "déclin",
        "predictions": predictions,
        "reliability": "high" if len(checkins) > 10 else "medium" if len(checkins) > 5 else "low"
    }

def get_prediction_description(score: float) -> str:
    """Description du score prédit"""
    if score >= 8:
        return "Peau excellente, très peu d'imperfections"
    elif score >= 7:
        return "Peau en bonne santé avec quelques améliorations possibles"
    elif score >= 6:
        return "Peau correcte avec des problèmes mineurs"
    elif score >= 5:
        return "Peau moyenne nécessitant des soins réguliers"
    elif score >= 4:
        return "Peau problématique nécessitant une attention particulière"
    else:
        return "Peau nécessitant des soins intensifs"

def generate_smart_tips(profile: Dict, checkins: List[Dict], photos: List[Dict]) -> List[Dict]:
    """Génère des conseils intelligents"""
    tips = []
    
    recent_checkins = sorted(checkins, key=lambda x: x["created_at"])[-5:] if checkins else []
    
    # Analyse des patterns de stress
    if recent_checkins:
        avg_stress = sum(c["stress_level"] for c in recent_checkins) / len(recent_checkins)
        avg_skin = sum(c["skin_condition"] for c in recent_checkins) / len(recent_checkins)
        
        if avg_stress > 7 and avg_skin < 6:
            tips.append({
                "type": "lifestyle",
                "priority": "high",
                "title": "Gestion du stress recommandée",
                "description": "Votre niveau de stress élevé peut impacter votre peau. Essayez la méditation ou le yoga.",
                "actionable": True,
                "estimated_impact": "high"
            })
    
    # Conseils basés sur le type de peau
    skin_type = profile.get("skin_type", "normale")
    concerns = profile.get("main_concerns", [])
    
    if skin_type == "grasse" and "acné" in concerns:
        tips.append({
            "type": "product",
            "priority": "high",
            "title": "Ajoutez un exfoliant chimique",
            "description": "L'acide salicylique (BHA) peut considérablement améliorer l'acné sur peau grasse.",
            "actionable": True,
            "estimated_impact": "high"
        })
    
    return tips

# Créer l'application
app = FastAPI(title="SkinCare SaaS API", version="1.0.0")

# CORS pour permettre les requêtes depuis le frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration simple
SECRET_KEY = "skincare-secret-key-2024"
ALGORITHM = "HS256"

# Stockage temporaire en mémoire (pour test)
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
from fastapi.responses import HTMLResponse

@app.get("/")
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
                font-family: Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-align: center;
                padding: 50px;
            }
            h1 { font-size: 3em; margin-bottom: 20px; }
            p { font-size: 1.2em; }
            .btn {
                display: inline-block;
                margin: 20px;
                padding: 15px 30px;
                background: white;
                color: #764ba2;
                text-decoration: none;
                border-radius: 25px;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <h1>🌸 SkinCare App</h1>
        <p>Ton coach beauté personnel avec IA</p>
        <a href="/docs" class="btn">Explorer l'API</a>
        <a href="/health" class="btn">Statut</a>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
    
@app.get("/health")
def health_check():
    return {
        "status": "OK", 
        "app": "SkinCare API",
        "users_count": len(users_db),
        "profiles_count": len(profiles_db)
    }

@app.post("/auth/register")
def register(user_data: UserRegistration):
    # Vérifier si email existe déjà
    if any(u["email"] == user_data.email for u in users_db.values()):
        raise HTTPException(status_code=400, detail="Email déjà utilisé")
    
    # Créer nouvel utilisateur
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
    # Chercher utilisateur
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
    # Simpler pour test - pas de token pour l'instant
    user_id = f"user_1"  # User par défaut pour test
    
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
    user_id = "user_1"  # User par défaut pour test
    if user_id not in profiles_db:
        raise HTTPException(status_code=404, detail="Profil non trouvé")
    return profiles_db[user_id]

@app.post("/checkin")
def daily_checkin(checkin: DailyCheckIn):
    user_id = "user_1"  # User par défaut pour test
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
    user_id = "user_1"  # User par défaut pour test
    user_checkins = [c for c in checkins_db.values() if c["user_id"] == user_id]
    return {"checkins": user_checkins, "count": len(user_checkins)}

@app.post("/photos/upload")
async def upload_photo(file: UploadFile = File(...), photo_type: str = "progress"):
    user_id = "user_1"  # User par défaut pour test
    
    # Vérifier le type de fichier
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Le fichier doit être une image")
    
    # Générer un nom unique pour la photo
    photo_id = str(uuid.uuid4())
    filename = f"{photo_id}_{file.filename}"
    
    photo_data = {
        "id": photo_id,
        "user_id": user_id,
        "filename": filename,
        "type": photo_type,
        "upload_date": datetime.utcnow().isoformat(),
        "size": file.size if hasattr(file, 'size') else 0
    }
    
    photos_db[photo_id] = photo_data
    
    return {
        "message": "Photo uploadée avec succès !",
        "photo_id": photo_id,
        "photo": photo_data
    }

@app.get("/photos/gallery")
async def get_photo_gallery():
    user_id = "user_1"  # User par défaut pour test
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
        "consistency_score": round((len(user_checkins) / 30) * 100, 1),
        "recent_checkins": user_checkins[-7:] if len(user_checkins) >= 7 else user_checkins
    }
    
    return analytics

# === ROUTES IA AVANCÉES ===

@app.get("/ai/recommendations")
async def get_ai_recommendations():
    """Recommandations IA personnalisées"""
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
        "high_priority": len([r for r in recommendations if r.get("urgency") == "high"]),
        "generated_at": datetime.utcnow().isoformat()
    }

@app.get("/ai/predictions")
async def get_future_predictions():
    """Prédictions d'amélioration futures"""
    user_id = "user_1"
    
    profile = profiles_db.get(user_id, {})
    checkins = [c for c in checkins_db.values() if c["user_id"] == user_id]
    
    if not profile:
        return {"message": "Créez d'abord votre profil"}
    
    predictions = predict_future_results(profile, checkins)
    
    return {
        "predictions": predictions,
        "data_quality": "high" if len(checkins) > 10 else "medium" if len(checkins) > 5 else "low",
        "generated_at": datetime.utcnow().isoformat()
    }

@app.get("/ai/smart-tips")
async def get_smart_tips():
    """Conseils intelligents personnalisés"""
    user_id = "user_1"
    
    profile = profiles_db.get(user_id, {})
    checkins = [c for c in checkins_db.values() if c["user_id"] == user_id]
    photos = [p for p in photos_db.values() if p["user_id"] == user_id]
    
    if not profile:
        return {"message": "Créez d'abord votre profil", "tips": []}
    
    tips = generate_smart_tips(profile, checkins, photos)
    
    return {
        "tips": tips,
        "high_priority_tips": [t for t in tips if t.get("priority") == "high"],
        "actionable_tips": [t for t in tips if t.get("actionable")],
        "total_tips": len(tips),
        "generated_at": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
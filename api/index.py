from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SkinCare SaaS API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Route de base
@app.get("/")
def hello():
    return {"message": "Hello ! Ton API SkinCare fonctionne ! 🎉", "status": "OK"}

# Route de test
@app.get("/test")
def test():
    return {"test": "API en ligne", "platform": "Vercel"}

# Route pour la santé
@app.get("/health")
def health():
    return {"status": "healthy", "app": "SkinCare"}
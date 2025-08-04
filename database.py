from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration base de données
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Table des utilisateurs
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    first_name = Column(String)
    age = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

# Table des profils de peau
class SkinProfile(Base):
    __tablename__ = "skin_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    skin_type = Column(String)
    main_concerns = Column(Text)  # JSON string
    stress_level = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

# Table des check-ins quotidiens
class DailyCheckIn(Base):
    __tablename__ = "daily_checkins"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    date = Column(String)
    skin_condition = Column(Integer)
    stress_level = Column(Integer)
    sleep_hours = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

# Fonction pour créer les tables
def create_tables():
    Base.metadata.create_all(bind=engine)
    print("✅ Tables créées avec succès !")

if __name__ == "__main__":
    create_tables()
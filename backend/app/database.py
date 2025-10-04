import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv, find_dotenv
from pathlib import Path

# Load variables from .env (robust to run from project root or /backend)
env_path = find_dotenv(filename=".env") or str(Path(__file__).resolve().parents[2] / ".env")
load_dotenv(env_path)

# Read DATABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(f"Missing DATABASE_URL (checked {env_path}). Put it in your project root .env.")

# Engine (connection pool)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Session factory
SessionLocal = sessionmaker(bind=engine, autoflush=False)  # add expire_on_commit=False if you want

# Base for ORM models
Base = declarative_base()

# Dependency for FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

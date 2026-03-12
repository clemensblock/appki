"""
Datenbankverbindung und Session-Management für app.ki
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://appki_user:passwort@localhost:5432/appki")

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency für FastAPI — liefert eine DB-Session pro Request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

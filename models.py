"""
SQLAlchemy-Modelle für die app.ki Datenbank.
Tabellen: ai_news und ai_tools
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from database import Base


class AiNews(Base):
    """Tabelle für KI-News-Artikel aus verschiedenen Quellen."""
    __tablename__ = "ai_news"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(Text, nullable=False)
    url = Column(Text, unique=True, nullable=False)
    summary = Column(Text, nullable=True)
    source = Column(String(100), nullable=True)       # z.B. 'techcrunch', 'therundown', 'venturebeat'
    category = Column(String(50), nullable=True)       # z.B. 'news', 'model', 'funding'
    published_at = Column(DateTime(timezone=True), nullable=True)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<AiNews(id={self.id}, title='{self.title[:50]}...', source='{self.source}')>"


class AiTools(Base):
    """Tabelle für KI-Tool-Einträge aus verschiedenen Verzeichnissen."""
    __tablename__ = "ai_tools"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    url = Column(Text, unique=True, nullable=True)
    pricing = Column(String(50), nullable=True)        # z.B. 'free', 'freemium', 'paid'
    category = Column(String(100), nullable=True)      # z.B. 'image', 'text', 'coding', 'video'
    source = Column(String(100), nullable=True)        # z.B. 'futurepedia', 'futuretools'
    status = Column(String(20), server_default="pending")  # 'pending', 'done', 'error'
    features = Column(JSONB, nullable=True)            # Liste der wichtigsten Features (JSON-Array)
    target_audience = Column(Text, nullable=True)      # Zielgruppe, 1 Satz
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    enriched_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<AiTools(id={self.id}, name='{self.name}', status='{self.status}')>"

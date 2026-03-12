"""
SQLAlchemy-Modelle für die app.ki Datenbank.
Tabellen: ai_news und ai_tools
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Index, func
from sqlalchemy.dialects.postgresql import JSONB
from database import Base


class AiNews(Base):
    """Tabelle fuer KI-News-Artikel aus verschiedenen Quellen."""
    __tablename__ = "ai_news"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(Text, nullable=False)
    url = Column(Text, unique=True, nullable=False)
    summary = Column(Text, nullable=True)
    source = Column(String(100), nullable=True)       # z.B. 'techcrunch', 'therundown', 'venturebeat'
    category = Column(String(50), nullable=True)       # z.B. 'industry', 'enterprise', 'releases'
    published_at = Column(DateTime(timezone=True), nullable=True)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    # Deutsche Uebersetzung und Zusammenfassung (via OpenAI)
    title_de = Column(Text, nullable=True)
    summary_de = Column(Text, nullable=True)          # 3-5 Saetze auf Deutsch
    enrichment_status = Column(String(20), server_default="pending")  # 'pending', 'done', 'error'
    enriched_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_ai_news_source", "source"),
        Index("ix_ai_news_published_at", "published_at"),
        Index("ix_ai_news_enrichment_status", "enrichment_status"),
    )

    def __repr__(self):
        return f"<AiNews(id={self.id}, title='{self.title[:50]}...', source='{self.source}')>"


class AiTools(Base):
    """Tabelle fuer KI-Tool-Eintraege aus verschiedenen Verzeichnissen."""
    __tablename__ = "ai_tools"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(220), unique=True, nullable=True)  # URL-freundlicher Name
    description = Column(Text, nullable=True)
    url = Column(Text, unique=True, nullable=True)
    website_url = Column(Text, nullable=True)          # Echte Tool-URL (nicht Futurepedia-Wrapper)
    pricing = Column(String(50), nullable=True)        # z.B. 'free', 'freemium', 'paid'
    category = Column(String(100), nullable=True)      # z.B. 'image', 'text', 'coding', 'video'
    source = Column(String(100), nullable=True)        # z.B. 'futurepedia', 'futuretools'
    status = Column(String(20), server_default="pending")  # 'pending', 'done', 'error'
    retry_count = Column(Integer, server_default="0")  # Anzahl fehlgeschlagener Versuche
    features = Column(JSONB, nullable=True)            # Liste der wichtigsten Features (JSON-Array)
    target_audience = Column(Text, nullable=True)      # Zielgruppe, 1 Satz
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    enriched_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_ai_tools_status", "status"),
        Index("ix_ai_tools_category", "category"),
        Index("ix_ai_tools_slug", "slug"),
    )

    def __repr__(self):
        return f"<AiTools(id={self.id}, name='{self.name}', status='{self.status}')>"

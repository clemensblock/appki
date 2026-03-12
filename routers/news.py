"""
API-Router für KI-News Endpoints.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
from models import AiNews
from schemas import NewsResponse

router = APIRouter(prefix="/api/news", tags=["News"])


@router.get("/sources", response_model=List[str], summary="Alle verfügbaren News-Quellen")
def get_news_sources(db: Session = Depends(get_db)):
    """Gibt eine Liste aller vorhandenen News-Quellen zurück."""
    sources = db.query(AiNews.source).distinct().filter(AiNews.source.isnot(None)).all()
    return [s[0] for s in sources]


@router.get("", response_model=List[NewsResponse], summary="News-Liste mit Filtern")
def get_news(
    source: Optional[str] = Query(None, description="Nach Quelle filtern"),
    category: Optional[str] = Query(None, description="Nach Kategorie filtern"),
    limit: int = Query(20, ge=1, le=100, description="Maximale Anzahl Ergebnisse"),
    offset: int = Query(0, ge=0, description="Offset für Pagination"),
    db: Session = Depends(get_db),
):
    """Gibt eine Liste von KI-News zurück, optional gefiltert nach Quelle und Kategorie."""
    query = db.query(AiNews)

    if source:
        query = query.filter(AiNews.source == source)
    if category:
        query = query.filter(AiNews.category == category)

    query = query.order_by(desc(AiNews.published_at), desc(AiNews.fetched_at))
    news = query.offset(offset).limit(limit).all()
    return news


@router.get("/{news_id}", response_model=NewsResponse, summary="Einzelner News-Eintrag")
def get_news_by_id(news_id: int, db: Session = Depends(get_db)):
    """Gibt einen einzelnen News-Eintrag anhand seiner ID zurück."""
    news = db.query(AiNews).filter(AiNews.id == news_id).first()
    if not news:
        raise HTTPException(status_code=404, detail="News-Eintrag nicht gefunden")
    return news

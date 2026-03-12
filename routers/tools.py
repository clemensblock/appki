"""
API-Router für KI-Tools Endpoints.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
from models import AiTools
from schemas import ToolResponse

router = APIRouter(prefix="/api/tools", tags=["Tools"])


@router.get("/categories", response_model=List[str], summary="Alle Tool-Kategorien")
def get_tool_categories(db: Session = Depends(get_db)):
    """Gibt eine Liste aller vorhandenen Tool-Kategorien zurück."""
    categories = db.query(AiTools.category).distinct().filter(AiTools.category.isnot(None)).all()
    return [c[0] for c in categories]


@router.get("", response_model=List[ToolResponse], summary="Tools-Liste mit Filtern")
def get_tools(
    source: Optional[str] = Query(None, description="Nach Quelle filtern"),
    category: Optional[str] = Query(None, description="Nach Kategorie filtern"),
    pricing: Optional[str] = Query(None, description="Nach Preismodell filtern"),
    limit: int = Query(20, ge=1, le=100, description="Maximale Anzahl Ergebnisse"),
    offset: int = Query(0, ge=0, description="Offset für Pagination"),
    db: Session = Depends(get_db),
):
    """Gibt eine Liste von KI-Tools zurück, optional gefiltert."""
    query = db.query(AiTools)

    if source:
        query = query.filter(AiTools.source == source)
    if category:
        query = query.filter(AiTools.category == category)
    if pricing:
        query = query.filter(AiTools.pricing == pricing)

    query = query.order_by(desc(AiTools.fetched_at))
    tools = query.offset(offset).limit(limit).all()
    return tools


@router.get("/{tool_id}", response_model=ToolResponse, summary="Einzelnes Tool")
def get_tool_by_id(tool_id: int, db: Session = Depends(get_db)):
    """Gibt ein einzelnes KI-Tool anhand seiner ID zurück."""
    tool = db.query(AiTools).filter(AiTools.id == tool_id).first()
    if not tool:
        raise HTTPException(status_code=404, detail="Tool nicht gefunden")
    return tool

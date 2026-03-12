"""
Pydantic-Schemas für Validierung und Serialisierung der API-Antworten.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# --- News Schemas ---

class NewsBase(BaseModel):
    title: str
    url: str
    summary: Optional[str] = None
    source: Optional[str] = None
    category: Optional[str] = None
    published_at: Optional[datetime] = None

class NewsResponse(NewsBase):
    id: int
    fetched_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Tools Schemas ---

class ToolBase(BaseModel):
    name: str
    description: Optional[str] = None
    url: Optional[str] = None
    pricing: Optional[str] = None
    category: Optional[str] = None
    source: Optional[str] = None

class ToolResponse(ToolBase):
    id: int
    fetched_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Statistik-Schema ---

class StatsResponse(BaseModel):
    news_gesamt: int
    tools_gesamt: int


# --- Status-Schema ---

class StatusResponse(BaseModel):
    status: str
    version: str
    project: str

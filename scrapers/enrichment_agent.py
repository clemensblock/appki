"""
Enrichment Agent (Stufe 2) fuer die app.ki 2-Stufen-Pipeline.

Laedt Details fuer Tools nach, die vom Collector (Stufe 1) gesammelt wurden:
1. Tool-Seite mit Firecrawl scrapen
2. Markdown an Claude API schicken fuer strukturierte Extraktion
3. Ergebnis in die Datenbank schreiben

Status-Uebergaenge:
  'pending' → 'done'   (erfolgreich angereichert)
  'pending' → 'error'  (Fehler bei Scraping oder Extraktion)
"""

import os
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional

import httpx
from firecrawl import FirecrawlApp
from sqlalchemy.orm import Session
from sqlalchemy import text

from models import AiTools

logger = logging.getLogger(__name__)

# Konfiguration aus Umgebungsvariablen
ENRICHMENT_BATCH_SIZE = int(os.getenv("ENRICHMENT_BATCH_SIZE", "50"))
SCRAPE_DELAY = 2  # Sekunden zwischen Tool-Scrapes

# Claude API Konfiguration
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# Prompt fuer die Extraktion
EXTRACTION_PROMPT = """Extrahiere aus diesem Text folgende Informationen als JSON:
- description (kurze Beschreibung, max 200 Zeichen, auf Deutsch)
- pricing ('free', 'freemium' oder 'paid')
- category (z.B. 'image', 'text', 'coding', 'video', 'audio', 'productivity')
- features (Liste der 3 wichtigsten Features, auf Deutsch)
- target_audience (Zielgruppe, 1 Satz, auf Deutsch)
Antworte NUR mit validem JSON, kein Text drumherum."""


def _get_anthropic_key() -> Optional[str]:
    """Liest den Anthropic API Key aus der Umgebung."""
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        logger.error("ANTHROPIC_API_KEY ist nicht gesetzt!")
        return None
    return key


def _get_firecrawl_client() -> Optional[FirecrawlApp]:
    """Erstellt einen Firecrawl-Client mit dem API-Key aus der Umgebung."""
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        logger.error("FIRECRAWL_API_KEY ist nicht gesetzt!")
        return None
    return FirecrawlApp(api_key=api_key)


def _scrape_tool_page(client: FirecrawlApp, url: str) -> Optional[str]:
    """Scrapt die Tool-Detailseite mit Firecrawl und gibt Markdown zurueck."""
    try:
        result = client.scrape_url(url, params={"formats": ["markdown"]})
        markdown = result.get("markdown", "")
        if not markdown:
            logger.warning(f"Enrichment: Kein Markdown fuer {url}")
            return None
        # Markdown auf 8000 Zeichen begrenzen (API-Token sparen)
        if len(markdown) > 8000:
            markdown = markdown[:8000]
        return markdown
    except Exception as e:
        logger.warning(f"Enrichment: Firecrawl-Scrape fehlgeschlagen fuer {url}: {e}")
        return None


def _extract_with_claude(markdown: str, tool_name: str, anthropic_key: str) -> Optional[dict]:
    """
    Schickt das Markdown an die Claude API und extrahiert strukturierte Daten.
    Gibt ein Dict mit description, pricing, category, features, target_audience zurueck.
    """
    try:
        headers = {
            "x-api-key": anthropic_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        payload = {
            "model": CLAUDE_MODEL,
            "max_tokens": 500,
            "messages": [
                {
                    "role": "user",
                    "content": f"Tool: {tool_name}\n\n{EXTRACTION_PROMPT}\n\nText:\n{markdown}",
                }
            ],
        }

        with httpx.Client(timeout=30.0) as http_client:
            response = http_client.post(ANTHROPIC_API_URL, json=payload, headers=headers)
            response.raise_for_status()

        result = response.json()
        content_text = result.get("content", [{}])[0].get("text", "")

        if not content_text:
            logger.warning(f"Enrichment: Leere Antwort von Claude fuer {tool_name}")
            return None

        # JSON aus der Antwort extrahieren
        # Claude antwortet manchmal mit Markdown-Code-Bloecken
        clean_text = content_text.strip()
        if clean_text.startswith("```"):
            # Code-Block entfernen
            lines = clean_text.split("\n")
            # Erste und letzte Zeile (```) entfernen
            json_lines = []
            in_block = False
            for line in lines:
                if line.strip().startswith("```") and not in_block:
                    in_block = True
                    continue
                elif line.strip() == "```" and in_block:
                    break
                elif in_block:
                    json_lines.append(line)
            clean_text = "\n".join(json_lines)

        data = json.loads(clean_text)
        return data

    except json.JSONDecodeError as e:
        logger.warning(f"Enrichment: JSON-Parse-Fehler fuer {tool_name}: {e}")
        return None
    except httpx.HTTPStatusError as e:
        logger.warning(f"Enrichment: Claude API HTTP-Fehler fuer {tool_name}: {e}")
        return None
    except Exception as e:
        logger.warning(f"Enrichment: Unerwarteter Fehler bei Claude-Extraktion fuer {tool_name}: {e}")
        return None


def _update_tool(db: Session, tool_id: int, data: dict) -> None:
    """Aktualisiert ein Tool mit den extrahierten Daten und setzt status='done'."""
    description = data.get("description", "")
    if description and len(description) > 2000:
        description = description[:2000]

    pricing = data.get("pricing", "")
    if pricing:
        pricing = pricing.lower().strip()
        if pricing not in ("free", "freemium", "paid"):
            pricing = None

    category = data.get("category", "")
    if category:
        category = category.lower().strip()[:100]

    features = data.get("features")
    if features and not isinstance(features, list):
        features = None

    target_audience = data.get("target_audience", "")
    if target_audience and len(target_audience) > 500:
        target_audience = target_audience[:500]

    db.execute(
        text("""
            UPDATE ai_tools SET
                description = :description,
                pricing = :pricing,
                category = :category,
                features = :features,
                target_audience = :target_audience,
                status = 'done',
                enriched_at = :enriched_at
            WHERE id = :tool_id
        """),
        {
            "description": description or None,
            "pricing": pricing or None,
            "category": category or None,
            "features": json.dumps(features) if features else None,
            "target_audience": target_audience or None,
            "enriched_at": datetime.now(timezone.utc),
            "tool_id": tool_id,
        },
    )
    db.commit()


def _mark_error(db: Session, tool_id: int) -> None:
    """Setzt den Status eines Tools auf 'error'."""
    db.execute(
        text("UPDATE ai_tools SET status = 'error' WHERE id = :tool_id"),
        {"tool_id": tool_id},
    )
    db.commit()


def enrich_pending_tools(db: Session) -> dict:
    """
    Enrichment Agent (Stufe 2): Holt Details fuer alle Tools mit status='pending'.

    Ablauf pro Tool:
      1. Tool-URL mit Firecrawl scrapen
      2. Markdown an Claude API schicken
      3. Extrahierte Daten in DB schreiben (status → 'done')
      4. Bei Fehler: status → 'error'

    Rate Limiting: 2 Sekunden zwischen jedem Tool.
    Batch-Groesse: maximal ENRICHMENT_BATCH_SIZE Tools pro Lauf.

    Gibt ein Dict mit Statistiken zurueck:
      {"enriched": N, "errors": M, "skipped": K}
    """
    anthropic_key = _get_anthropic_key()
    if not anthropic_key:
        return {"enriched": 0, "errors": 0, "skipped": 0, "error": "ANTHROPIC_API_KEY fehlt"}

    firecrawl_client = _get_firecrawl_client()
    if not firecrawl_client:
        return {"enriched": 0, "errors": 0, "skipped": 0, "error": "FIRECRAWL_API_KEY fehlt"}

    # Pending Tools laden (aelteste zuerst, limitiert auf Batch-Groesse)
    pending_tools = (
        db.query(AiTools)
        .filter(AiTools.status == "pending")
        .order_by(AiTools.fetched_at.asc())
        .limit(ENRICHMENT_BATCH_SIZE)
        .all()
    )

    if not pending_tools:
        logger.info("Enrichment: Keine pending Tools vorhanden.")
        return {"enriched": 0, "errors": 0, "skipped": 0}

    logger.info(f"=== Enrichment Agent gestartet: {len(pending_tools)} Tools zu verarbeiten ===")

    enriched = 0
    errors = 0

    for tool in pending_tools:
        try:
            logger.info(f"Enrichment: Verarbeite '{tool.name}' ({tool.url})")

            # 1. Tool-Seite scrapen
            markdown = _scrape_tool_page(firecrawl_client, tool.url)
            if not markdown:
                logger.warning(f"Enrichment: Kein Inhalt fuer '{tool.name}' — markiere als error")
                _mark_error(db, tool.id)
                errors += 1
                time.sleep(SCRAPE_DELAY)
                continue

            # 2. Mit Claude extrahieren
            data = _extract_with_claude(markdown, tool.name, anthropic_key)
            if not data:
                logger.warning(f"Enrichment: Extraktion fehlgeschlagen fuer '{tool.name}' — markiere als error")
                _mark_error(db, tool.id)
                errors += 1
                time.sleep(SCRAPE_DELAY)
                continue

            # 3. Tool aktualisieren
            _update_tool(db, tool.id, data)
            enriched += 1
            logger.info(f"Enrichment: '{tool.name}' erfolgreich angereichert")

        except Exception as e:
            logger.error(f"Enrichment: Unerwarteter Fehler bei '{tool.name}': {e}")
            try:
                _mark_error(db, tool.id)
            except Exception:
                db.rollback()
            errors += 1

        # Rate Limiting
        time.sleep(SCRAPE_DELAY)

    logger.info(f"=== Enrichment abgeschlossen: {enriched} angereichert, {errors} Fehler ===")
    return {"enriched": enriched, "errors": errors, "skipped": 0}

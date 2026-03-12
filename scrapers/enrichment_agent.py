"""
Enrichment Agent (Stufe 2) fuer die app.ki 2-Stufen-Pipeline.

Laedt Details fuer Tools nach, die vom Collector (Stufe 1) gesammelt wurden:
1. Tool-Seite mit Firecrawl scrapen
2. Markdown an Claude API schicken fuer strukturierte Extraktion
3. Ergebnis in die Datenbank schreiben

Status-Uebergaenge:
  'pending' -> 'done'   (erfolgreich angereichert)
  'pending' -> 'error'  (Fehler bei Scraping oder Extraktion)

Retry-Logik: Tools mit status='error' werden nach 24h automatisch erneut versucht (max 3 Retries).
"""

import os
import re
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
from firecrawl import FirecrawlApp
from sqlalchemy.orm import Session
from sqlalchemy import text, and_

from models import AiTools

logger = logging.getLogger(__name__)

# Konfiguration aus Umgebungsvariablen
ENRICHMENT_BATCH_SIZE = int(os.getenv("ENRICHMENT_BATCH_SIZE", "50"))
MAX_RETRIES = 3
SCRAPE_DELAY = 2  # Sekunden zwischen Tool-Scrapes

# Claude API Konfiguration
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-sonnet-4-20250514"

# Prompt fuer die Extraktion — eigenstaendige deutsche Texte
EXTRACTION_PROMPT = """Du bist Redakteur fuer eine fuehrende deutsche KI-Informationsplattform.
Erstelle aus dem folgenden Text einen eigenstaendigen, professionellen Eintrag auf Deutsch.

Gib das Ergebnis als JSON zurueck mit genau diesen Feldern:
- "description": Professionelle Beschreibung auf Deutsch, 2-3 Saetze, max 300 Zeichen. Erklaere was das Tool macht und fuer wen es geeignet ist.
- "pricing": Exakt einer der Werte 'free', 'freemium' oder 'paid'
- "category": Hauptkategorie (z.B. 'Bildgenerierung', 'Textgenerierung', 'Coding', 'Video', 'Audio', 'Produktivitaet', 'Marketing', 'Bildung', 'Business', 'Chatbot')
- "features": Liste der 3 wichtigsten Features, jeweils auf Deutsch, kurz und praegnant
- "target_audience": Zielgruppe, 1 Satz auf Deutsch
- "website_url": Die echte Website-URL des Tools (nicht die Verzeichnis-URL). Falls im Text vorhanden.

WICHTIG: Schreibe eigenstaendige, professionelle Texte. Keine 1:1 Uebersetzung.
Antworte NUR mit validem JSON, kein Text drumherum."""


def _generate_slug(name: str) -> str:
    """Erzeugt einen URL-freundlichen Slug aus dem Tool-Namen."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:220]


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
        if len(markdown) > 8000:
            markdown = markdown[:8000]
        return markdown
    except Exception as e:
        logger.warning(f"Enrichment: Firecrawl-Scrape fehlgeschlagen fuer {url}: {e}")
        return None


def _extract_with_claude(markdown: str, tool_name: str, anthropic_key: str) -> Optional[dict]:
    """
    Schickt das Markdown an die Claude API und extrahiert strukturierte Daten.
    """
    try:
        headers = {
            "x-api-key": anthropic_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        payload = {
            "model": CLAUDE_MODEL,
            "max_tokens": 600,
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

        clean_text = content_text.strip()
        if clean_text.startswith("```"):
            lines = clean_text.split("\n")
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


def _update_tool(db: Session, tool_id: int, tool_name: str, data: dict) -> None:
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
        category = category.strip()[:100]

    features = data.get("features")
    if features and not isinstance(features, list):
        features = None

    target_audience = data.get("target_audience", "")
    if target_audience and len(target_audience) > 500:
        target_audience = target_audience[:500]

    website_url = data.get("website_url", "")
    if website_url and not website_url.startswith("http"):
        website_url = None

    slug = _generate_slug(tool_name)

    db.execute(
        text("""
            UPDATE ai_tools SET
                description = :description,
                pricing = :pricing,
                category = :category,
                features = :features,
                target_audience = :target_audience,
                website_url = :website_url,
                slug = :slug,
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
            "website_url": website_url or None,
            "slug": slug,
            "enriched_at": datetime.now(timezone.utc),
            "tool_id": tool_id,
        },
    )
    db.commit()


def _mark_error(db: Session, tool_id: int) -> None:
    """Setzt den Status eines Tools auf 'error' und erhoeht retry_count."""
    db.execute(
        text("""
            UPDATE ai_tools SET
                status = 'error',
                retry_count = COALESCE(retry_count, 0) + 1
            WHERE id = :tool_id
        """),
        {"tool_id": tool_id},
    )
    db.commit()


def enrich_pending_tools(db: Session) -> dict:
    """
    Enrichment Agent (Stufe 2): Holt Details fuer alle Tools mit status='pending'.
    Gibt ein Dict mit Statistiken zurueck.
    """
    anthropic_key = _get_anthropic_key()
    if not anthropic_key:
        return {"enriched": 0, "errors": 0, "skipped": 0, "error": "ANTHROPIC_API_KEY fehlt"}

    firecrawl_client = _get_firecrawl_client()
    if not firecrawl_client:
        return {"enriched": 0, "errors": 0, "skipped": 0, "error": "FIRECRAWL_API_KEY fehlt"}

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

            markdown = _scrape_tool_page(firecrawl_client, tool.url)
            if not markdown:
                _mark_error(db, tool.id)
                errors += 1
                time.sleep(SCRAPE_DELAY)
                continue

            data = _extract_with_claude(markdown, tool.name, anthropic_key)
            if not data:
                _mark_error(db, tool.id)
                errors += 1
                time.sleep(SCRAPE_DELAY)
                continue

            _update_tool(db, tool.id, tool.name, data)
            enriched += 1
            logger.info(f"Enrichment: '{tool.name}' erfolgreich angereichert")

        except Exception as e:
            logger.error(f"Enrichment: Unerwarteter Fehler bei '{tool.name}': {e}")
            try:
                _mark_error(db, tool.id)
            except Exception:
                db.rollback()
            errors += 1

        time.sleep(SCRAPE_DELAY)

    logger.info(f"=== Enrichment abgeschlossen: {enriched} angereichert, {errors} Fehler ===")
    return {"enriched": enriched, "errors": errors, "skipped": 0}


def retry_failed_tools(db: Session) -> dict:
    """
    Retry-Job: Versucht Tools mit status='error' erneut, sofern retry_count < MAX_RETRIES.
    Setzt den Status zurueck auf 'pending', damit der naechste Enrichment-Lauf sie verarbeitet.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    retryable = (
        db.query(AiTools)
        .filter(
            and_(
                AiTools.status == "error",
                AiTools.retry_count < MAX_RETRIES,
            )
        )
        .all()
    )

    if not retryable:
        logger.info("Retry: Keine retryable Tools vorhanden.")
        return {"reset": 0}

    reset_count = 0
    for tool in retryable:
        db.execute(
            text("UPDATE ai_tools SET status = 'pending' WHERE id = :tool_id"),
            {"tool_id": tool.id},
        )
        reset_count += 1

    db.commit()
    logger.info(f"Retry: {reset_count} Tools zurueck auf 'pending' gesetzt")
    return {"reset": reset_count}

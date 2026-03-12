"""
Firecrawl-Scraper für KI-Tool-Verzeichnisse.
Nutzt die Firecrawl API für JavaScript-Rendering und Anti-Bot-Schutz.
"""

import os
import re
import logging
from typing import List, Dict, Optional

from firecrawl import FirecrawlApp
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from models import AiTools

logger = logging.getLogger(__name__)

# Zu scrapende Seiten
SCRAPE_TARGETS = [
    {
        "name": "futuretools",
        "url": "https://www.futuretools.io/newly-added",
        "source": "futuretools",
    },
    {
        "name": "futurepedia",
        "url": "https://www.futurepedia.io",
        "source": "futurepedia",
    },
]


def get_firecrawl_client() -> Optional[FirecrawlApp]:
    """Erstellt einen Firecrawl-Client mit dem API-Key aus der Umgebung."""
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        logger.error("FIRECRAWL_API_KEY ist nicht gesetzt!")
        return None
    return FirecrawlApp(api_key=api_key)


def parse_tools_from_markdown(markdown: str, source: str) -> List[Dict]:
    """
    Extrahiert Tool-Informationen aus dem Markdown-Text.
    Versucht Name, Beschreibung, URL, Pricing und Kategorie zu erkennen.
    """
    tools = []
    # Einfaches Parsing: Suche nach Überschriften und Links
    lines = markdown.split("\n")
    current_tool = {}

    for line in lines:
        line = line.strip()

        # Überschrift als Tool-Name erkennen
        heading_match = re.match(r"^#{1,3}\s+\[?([^\]#]+)\]?\(?([^)]*)\)?", line)
        if heading_match:
            # Vorheriges Tool speichern
            if current_tool.get("name"):
                tools.append(current_tool)
            current_tool = {
                "name": heading_match.group(1).strip(),
                "url": heading_match.group(2).strip() if heading_match.group(2) else None,
                "source": source,
                "description": "",
                "pricing": None,
                "category": None,
            }
            continue

        # Link als Tool erkennen
        link_match = re.match(r"^\*?\*?\[([^\]]+)\]\(([^)]+)\)\*?\*?(.*)$", line)
        if link_match and not current_tool.get("name"):
            if current_tool.get("name"):
                tools.append(current_tool)
            current_tool = {
                "name": link_match.group(1).strip(),
                "url": link_match.group(2).strip(),
                "source": source,
                "description": link_match.group(3).strip(" -–—:"),
                "pricing": None,
                "category": None,
            }
            continue

        # Beschreibung hinzufügen
        if current_tool.get("name") and line and not line.startswith("#"):
            if not current_tool.get("description"):
                current_tool["description"] = line
            # Pricing erkennen
            lower_line = line.lower()
            if "free" in lower_line and "freemium" not in lower_line:
                current_tool["pricing"] = "free"
            elif "freemium" in lower_line:
                current_tool["pricing"] = "freemium"
            elif "paid" in lower_line or "pricing" in lower_line or "$" in line:
                current_tool["pricing"] = "paid"

    # Letztes Tool speichern
    if current_tool.get("name"):
        tools.append(current_tool)

    return tools


def scrape_single_target(target: Dict, client: FirecrawlApp, db: Session) -> int:
    """
    Scrapt eine einzelne Zielseite und speichert die gefundenen Tools.
    Gibt die Anzahl neu gespeicherter Einträge zurück.
    """
    target_name = target["name"]
    target_url = target["url"]
    source = target["source"]
    new_count = 0

    try:
        logger.info(f"Scrape mit Firecrawl: {target_name} ({target_url})")

        # Versuche zuerst Extract, dann Fallback auf Scrape
        try:
            result = client.scrape_url(target_url, params={"formats": ["markdown"]})
            markdown_content = result.get("markdown", "")
        except Exception as e:
            logger.warning(f"Scrape für {target_name} fehlgeschlagen: {e}")
            return 0

        if not markdown_content:
            logger.warning(f"Kein Markdown-Inhalt für {target_name}")
            return 0

        # Tools aus Markdown extrahieren
        tools = parse_tools_from_markdown(markdown_content, source)
        logger.info(f"{target_name}: {len(tools)} Tools im Markdown gefunden")

        for tool in tools:
            if not tool.get("name") or not tool.get("url"):
                continue

            # Beschreibung kürzen falls zu lang
            description = tool.get("description", "")
            if description and len(description) > 2000:
                description = description[:2000] + "..."

            # Upsert mit ON CONFLICT DO NOTHING für Deduplizierung
            stmt = pg_insert(AiTools).values(
                name=tool["name"][:200],
                description=description,
                url=tool["url"],
                pricing=tool.get("pricing"),
                category=tool.get("category"),
                source=source,
            ).on_conflict_do_nothing(index_elements=["url"])

            result = db.execute(stmt)
            if result.rowcount > 0:
                new_count += 1

        db.commit()
        logger.info(f"{target_name}: {new_count} neue Tools gespeichert")

    except Exception as e:
        logger.error(f"Fehler beim Scrapen von {target_name}: {e}")
        db.rollback()

    return new_count


def scrape_all_tools(db: Session) -> int:
    """
    Scrapt alle konfigurierten Tool-Verzeichnisse.
    Fehler bei einer Seite stoppen nicht die anderen.
    Gibt die Gesamtanzahl neu gespeicherter Einträge zurück.
    """
    client = get_firecrawl_client()
    if not client:
        logger.error("Firecrawl-Client konnte nicht erstellt werden.")
        return 0

    total_new = 0
    logger.info("Starte Firecrawl-Scraping für alle Tool-Verzeichnisse...")

    for target in SCRAPE_TARGETS:
        try:
            count = scrape_single_target(target, client, db)
            total_new += count
        except Exception as e:
            logger.error(f"Unerwarteter Fehler bei {target['name']}: {e}")
            continue

    logger.info(f"Firecrawl-Scraping abgeschlossen. Insgesamt {total_new} neue Tools.")
    return total_new

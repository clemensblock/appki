"""
Firecrawl-Scraper fuer KI-Tool-Verzeichnisse.
Nutzt die Firecrawl API fuer JavaScript-Rendering und Anti-Bot-Schutz.
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


def parse_futuretools_markdown(markdown: str) -> List[Dict]:
    """
    Parst die Markdown-Ausgabe von FutureTools.
    Format:
      [ToolName](https://www.futuretools.io/tools/slug)
      Beschreibungstext
      [Kategorie](https://www.futuretools.io/?tags=...)
    """
    tools = []
    lines = markdown.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Tool-Link erkennen: [Name](https://www.futuretools.io/tools/...)
        tool_match = re.match(
            r"\[([^\]]+)\]\((https?://www\.futuretools\.io/tools/[^)]+)\)",
            line,
        )
        if tool_match:
            name = tool_match.group(1).strip()
            tool_url = tool_match.group(2).strip()
            description = ""
            category = None

            # Naechste Zeilen nach Beschreibung und Kategorie durchsuchen
            j = i + 1
            while j < len(lines) and j < i + 5:
                next_line = lines[j].strip()
                if not next_line:
                    j += 1
                    continue

                # Kategorie-Link erkennen (beide URL-Formate)
                cat_match = re.match(
                    r"\[([^\]]+)\]\(https?://www\.futuretools\.io/\?tags",
                    next_line,
                )
                if cat_match:
                    category = cat_match.group(1).strip()
                    j += 1
                    continue

                # Wenn kein Link und keine leere Zeile: Beschreibung
                if not next_line.startswith("[") and not next_line.startswith("!"):
                    if not description:
                        description = next_line
                j += 1

            # Nur echte Tools speichern (nicht Footer-Links etc.)
            if name and len(name) < 100:
                tools.append({
                    "name": name,
                    "url": tool_url,
                    "description": description,
                    "category": category.lower() if category else None,
                    "pricing": None,
                    "source": "futuretools",
                })
            i = j if j > i + 1 else i + 1
        else:
            i += 1

    return tools


def parse_futurepedia_markdown(markdown: str) -> List[Dict]:
    """
    Parst die Markdown-Ausgabe von Futurepedia.
    Format:
      [ToolName](https://www.futurepedia.io/tool/slug)
      Beschreibungstext
      [#kategorie1](url) [#kategorie2](url)
    """
    tools = []
    lines = markdown.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Tool-Link erkennen: [Name](https://www.futurepedia.io/tool/...)
        tool_match = re.match(
            r"\[([^\]]+)\]\((https?://www\.futurepedia\.io/tool/[^)]+)\)",
            line,
        )
        if tool_match:
            name = tool_match.group(1).strip()
            tool_url = tool_match.group(2).strip()
            description = ""
            categories = []
            pricing = None

            # Naechste Zeilen nach Beschreibung und Kategorien durchsuchen
            j = i + 1
            while j < len(lines) and j < i + 8:
                next_line = lines[j].strip()
                if not next_line:
                    j += 1
                    continue

                # Duplikat-Name ueberspringen (Futurepedia wiederholt den Namen)
                if next_line == name:
                    j += 1
                    continue

                # Reine Zahl ueberspringen (z.B. "6226" Bewertungen)
                if re.match(r"^\d+$", next_line):
                    j += 1
                    continue

                # Kategorie-Tags erkennen: [#kategorie](url)
                cat_matches = re.findall(
                    r"\[#([^\]]+)\]\(https?://www\.futurepedia\.io/ai-tools/[^)]+\)",
                    next_line,
                )
                if cat_matches:
                    categories.extend(cat_matches)
                    j += 1
                    continue

                # Wenn naechster Tool-Link kommt, aufhoeren
                if re.match(
                    r"\[([^\]]+)\]\(https?://www\.futurepedia\.io/tool/",
                    next_line,
                ):
                    break

                # Bild-Links ueberspringen
                if next_line.startswith("[![") or next_line.startswith("!["):
                    j += 1
                    continue

                # Beschreibung (erste sinnvolle Textzeile)
                if (
                    not description
                    and not next_line.startswith("[")
                    and not next_line.startswith("#")
                    and len(next_line) > 10
                ):
                    description = next_line

                j += 1

            # Pricing aus Beschreibung/Kategorien ableiten
            all_text = (description + " " + " ".join(categories)).lower()
            if "free" in all_text and "freemium" not in all_text:
                pricing = "free"
            elif "freemium" in all_text:
                pricing = "freemium"
            elif "paid" in all_text or "$" in all_text:
                pricing = "paid"

            # Kategorie als komma-getrennte Liste
            category_str = ", ".join(categories[:3]) if categories else None

            # Nur echte Tools speichern
            if name and len(name) < 100 and "cookie" not in name.lower():
                tools.append({
                    "name": name,
                    "url": tool_url,
                    "description": description,
                    "category": category_str,
                    "pricing": pricing,
                    "source": "futurepedia",
                })
            i = j if j > i + 1 else i + 1
        else:
            i += 1

    return tools


def parse_tools_from_markdown(markdown: str, source: str) -> List[Dict]:
    """Waehlt den richtigen Parser basierend auf der Quelle."""
    if source == "futuretools":
        return parse_futuretools_markdown(markdown)
    elif source == "futurepedia":
        return parse_futurepedia_markdown(markdown)
    return _parse_generic_markdown(markdown, source)


def _parse_generic_markdown(markdown: str, source: str) -> List[Dict]:
    """Generisches Fallback-Parsing fuer unbekannte Quellen."""
    tools = []
    lines = markdown.split("\n")

    for line in lines:
        line = line.strip()
        link_match = re.match(r"\[([^\]]+)\]\((https?://[^)]+)\)", line)
        if link_match:
            name = link_match.group(1).strip()
            url = link_match.group(2).strip()
            if len(name) > 3 and len(name) < 100:
                tools.append({
                    "name": name,
                    "url": url,
                    "source": source,
                    "description": "",
                    "pricing": None,
                    "category": None,
                })

    return tools


def scrape_single_target(target: Dict, client: FirecrawlApp, db: Session) -> int:
    """
    Scrapt eine einzelne Zielseite und speichert die gefundenen Tools.
    Gibt die Anzahl neu gespeicherter Eintraege zurueck.
    """
    target_name = target["name"]
    target_url = target["url"]
    source = target["source"]
    new_count = 0

    try:
        logger.info(f"Scrape mit Firecrawl: {target_name} ({target_url})")

        # Seite mit Firecrawl scrapen
        try:
            result = client.scrape_url(target_url, params={"formats": ["markdown"]})
            markdown_content = result.get("markdown", "")
        except Exception as e:
            logger.warning(f"Scrape fuer {target_name} fehlgeschlagen: {e}")
            return 0

        if not markdown_content:
            logger.warning(f"Kein Markdown-Inhalt fuer {target_name}")
            return 0

        logger.info(f"{target_name}: Markdown erhalten ({len(markdown_content)} Zeichen)")

        # Tools aus Markdown extrahieren
        tools = parse_tools_from_markdown(markdown_content, source)
        logger.info(f"{target_name}: {len(tools)} Tools im Markdown gefunden")

        for tool in tools:
            if not tool.get("name") or not tool.get("url"):
                continue

            # Beschreibung kuerzen falls zu lang
            description = tool.get("description", "")
            if description and len(description) > 2000:
                description = description[:2000] + "..."

            # Upsert mit ON CONFLICT DO NOTHING fuer Deduplizierung
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
    Gibt die Gesamtanzahl neu gespeicherter Eintraege zurueck.
    """
    client = get_firecrawl_client()
    if not client:
        logger.error("Firecrawl-Client konnte nicht erstellt werden.")
        return 0

    total_new = 0
    logger.info("Starte Firecrawl-Scraping fuer alle Tool-Verzeichnisse...")

    for target in SCRAPE_TARGETS:
        try:
            count = scrape_single_target(target, client, db)
            total_new += count
        except Exception as e:
            logger.error(f"Unerwarteter Fehler bei {target['name']}: {e}")
            continue

    logger.info(f"Firecrawl-Scraping abgeschlossen. Insgesamt {total_new} neue Tools.")
    return total_new

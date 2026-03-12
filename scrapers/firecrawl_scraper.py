"""
Firecrawl-Scraper fuer KI-Tool-Verzeichnisse — STUFE 1: Collector.
Sammelt NUR Tool-Namen und URLs, speichert mit status='pending'.
Details werden vom Enrichment Agent (Stufe 2) nachgeladen.

Scrapt mehrere Seiten und Kategorien fuer maximale Tool-Abdeckung:
- FutureTools: Homepage + Newly Added
- Futurepedia: Mehrere Kategorie-Seiten (productivity, video, text, business, image, coding, etc.)
"""

import os
import re
import logging
import time
from typing import List, Dict, Optional

from firecrawl import FirecrawlApp
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from models import AiTools

logger = logging.getLogger(__name__)

# -- Zu scrapende Seiten --

# FutureTools — Homepage zeigt ~20 Tools, Newly Added ~4-10
FUTURETOOLS_URLS = [
    "https://www.futuretools.io/",
    "https://www.futuretools.io/newly-added",
]

# Futurepedia — Kategorie-Seiten mit je ~15-50 Tools
FUTUREPEDIA_CATEGORY_URLS = [
    "https://www.futurepedia.io/ai-tools/productivity",
    "https://www.futurepedia.io/ai-tools/video",
    "https://www.futurepedia.io/ai-tools/text-generators",
    "https://www.futurepedia.io/ai-tools/business",
    "https://www.futurepedia.io/ai-tools/image",
    "https://www.futurepedia.io/ai-tools/code-assistant",
    "https://www.futurepedia.io/ai-tools/marketing",
    "https://www.futurepedia.io/ai-tools/chatbots",
    "https://www.futurepedia.io/ai-tools/education",
    "https://www.futurepedia.io/ai-tools/search-engine",
    "https://www.futurepedia.io/ai-tools/music",
    "https://www.futurepedia.io/ai-tools/finance",
    "https://www.futurepedia.io/ai-tools/customer-support",
    "https://www.futurepedia.io/ai-tools/social-media",
    "https://www.futurepedia.io/ai-tools/healthcare",
]

# Auch die Futurepedia-Startseite (Featured Tools)
FUTUREPEDIA_EXTRA_URLS = [
    "https://www.futurepedia.io",
]

# Pause zwischen Scrapes (Sekunden) — API-Rate-Limit beachten
SCRAPE_DELAY = 2


def get_firecrawl_client() -> Optional[FirecrawlApp]:
    """Erstellt einen Firecrawl-Client mit dem API-Key aus der Umgebung."""
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        logger.error("FIRECRAWL_API_KEY ist nicht gesetzt!")
        return None
    return FirecrawlApp(api_key=api_key)


# -- FutureTools Parser (nur Name + URL) --

def parse_futuretools_links(markdown: str) -> List[Dict]:
    """
    Extrahiert Tool-Namen und URLs aus FutureTools Markdown.
    Collector-Modus: nur Name und URL, keine Details.
    """
    tools = []
    seen_urls = set()

    for match in re.finditer(
        r"^\[([^\]!\[]+)\]\((https?://www\.futuretools\.io/tools/[^)]+)\)$",
        markdown,
        re.MULTILINE,
    ):
        name = match.group(1).strip()
        url = match.group(2).strip()

        # Duplikate innerhalb einer Seite vermeiden
        if url in seen_urls:
            continue
        seen_urls.add(url)

        # Nur echte Tool-Namen (keine Footer-Links, Navigation etc.)
        if name and 1 < len(name) < 100:
            tools.append({"name": name, "url": url, "source": "futuretools"})

    return tools


# -- Futurepedia Parser (nur Name + URL) --

def parse_futurepedia_links(markdown: str) -> List[Dict]:
    """
    Extrahiert Tool-Namen und URLs aus Futurepedia Markdown.
    Collector-Modus: nur Name und URL, keine Details.
    Funktioniert fuer Homepage und Kategorie-Seiten.
    """
    tools = []
    seen_urls = set()

    for match in re.finditer(
        r"\[([^\]]+)\]\((https?://www\.futurepedia\.io/tool/[^)]+)\)",
        markdown,
    ):
        name = match.group(1).strip()
        url = match.group(2).strip()

        # Rating-Links ausfiltern
        if "Rated" in name and "out of" in name:
            continue

        # Bild-Alt-Texte ausfiltern (enthalten "logo")
        if " logo" in name.lower():
            continue

        # Cookie-Banner etc. ausfiltern
        if "cookie" in name.lower():
            continue

        # Duplikate innerhalb einer Seite vermeiden
        if url in seen_urls:
            continue
        seen_urls.add(url)

        # Nur echte Tool-Namen
        if name and 1 < len(name) < 100:
            tools.append({"name": name, "url": url, "source": "futurepedia"})

    return tools


# -- Scraping-Logik --

def _scrape_url(client: FirecrawlApp, url: str) -> str:
    """Scrapt eine URL mit Firecrawl und gibt den Markdown-Inhalt zurueck."""
    try:
        result = client.scrape_url(url, params={"formats": ["markdown"]})
        return result.get("markdown", "")
    except Exception as e:
        logger.warning(f"Firecrawl-Scrape fehlgeschlagen fuer {url}: {e}")
        return ""


def _save_collected_tools(tools: List[Dict], source: str, db: Session) -> int:
    """
    Speichert gesammelte Tools (nur Name + URL) in die Datenbank.
    Neue Tools bekommen status='pending'.
    Bereits vorhandene Tools werden NICHT ueberschrieben (DO NOTHING).
    Gibt Anzahl neu eingefuegter Eintraege zurueck.
    """
    new_count = 0
    for tool in tools:
        if not tool.get("name") or not tool.get("url"):
            continue

        # INSERT ... ON CONFLICT DO NOTHING — nur neue Tools einfuegen
        stmt = pg_insert(AiTools).values(
            name=tool["name"][:200],
            url=tool["url"],
            source=source,
            status="pending",
        ).on_conflict_do_nothing(
            index_elements=["url"],
        )

        result = db.execute(stmt)
        if result.rowcount > 0:
            new_count += 1

    db.commit()
    return new_count


def collect_futuretools(client: FirecrawlApp, db: Session) -> int:
    """
    Collector fuer FutureTools: Homepage + Newly Added.
    Sammelt nur Namen und URLs.
    """
    total = 0

    for url in FUTURETOOLS_URLS:
        try:
            logger.info(f"Collector: Scrape FutureTools {url}")
            markdown = _scrape_url(client, url)
            if not markdown:
                continue

            tools = parse_futuretools_links(markdown)
            logger.info(f"Collector: FutureTools {url} — {len(tools)} Links gefunden")

            count = _save_collected_tools(tools, "futuretools", db)
            total += count
            logger.info(f"Collector: FutureTools {url} — {count} neue Tools gespeichert")

            time.sleep(SCRAPE_DELAY)
        except Exception as e:
            logger.error(f"Collector: Fehler bei FutureTools {url}: {e}")
            db.rollback()
            continue

    return total


def collect_futurepedia(client: FirecrawlApp, db: Session) -> int:
    """
    Collector fuer Futurepedia: Homepage + alle Kategorie-Seiten.
    Sammelt nur Namen und URLs.
    """
    total = 0

    # Homepage
    for url in FUTUREPEDIA_EXTRA_URLS:
        try:
            logger.info(f"Collector: Scrape Futurepedia Homepage {url}")
            markdown = _scrape_url(client, url)
            if not markdown:
                continue

            tools = parse_futurepedia_links(markdown)
            logger.info(f"Collector: Futurepedia Homepage — {len(tools)} Links gefunden")

            count = _save_collected_tools(tools, "futurepedia", db)
            total += count
            logger.info(f"Collector: Futurepedia Homepage — {count} neue Tools gespeichert")

            time.sleep(SCRAPE_DELAY)
        except Exception as e:
            logger.error(f"Collector: Fehler bei Futurepedia Homepage {url}: {e}")
            db.rollback()
            continue

    # Kategorie-Seiten
    for url in FUTUREPEDIA_CATEGORY_URLS:
        try:
            category_name = url.split("/")[-1]
            logger.info(f"Collector: Scrape Futurepedia Kategorie {category_name}")
            markdown = _scrape_url(client, url)
            if not markdown:
                continue

            tools = parse_futurepedia_links(markdown)
            logger.info(f"Collector: Futurepedia {category_name} — {len(tools)} Links gefunden")

            count = _save_collected_tools(tools, "futurepedia", db)
            total += count
            logger.info(f"Collector: Futurepedia {category_name} — {count} neue Tools gespeichert")

            time.sleep(SCRAPE_DELAY)
        except Exception as e:
            logger.error(f"Collector: Fehler bei Futurepedia {url}: {e}")
            db.rollback()
            continue

    return total


# -- Hauptfunktion --

def collect_all_tools(db: Session) -> int:
    """
    Collector (Stufe 1): Sammelt Tool-Namen und URLs aus allen Quellen.
    Speichert neue Tools mit status='pending'.
    Details werden spaeter vom Enrichment Agent (Stufe 2) nachgeladen.

    Gibt die Gesamtanzahl neu gespeicherter Eintraege zurueck.
    """
    client = get_firecrawl_client()
    if not client:
        logger.error("Firecrawl-Client konnte nicht erstellt werden.")
        return 0

    total_new = 0
    logger.info("=== Collector (Stufe 1) gestartet: Sammle Tool-Namen und URLs ===")

    # FutureTools
    try:
        ft_count = collect_futuretools(client, db)
        total_new += ft_count
        logger.info(f"Collector: FutureTools fertig — {ft_count} neue Tools")
    except Exception as e:
        logger.error(f"Collector: Unerwarteter Fehler bei FutureTools: {e}")

    # Futurepedia
    try:
        fp_count = collect_futurepedia(client, db)
        total_new += fp_count
        logger.info(f"Collector: Futurepedia fertig — {fp_count} neue Tools")
    except Exception as e:
        logger.error(f"Collector: Unerwarteter Fehler bei Futurepedia: {e}")

    logger.info(f"=== Collector abgeschlossen: {total_new} neue Tools gesammelt ===")
    return total_new

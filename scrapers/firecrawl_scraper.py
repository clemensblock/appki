"""
Firecrawl-Scraper fuer KI-Tool-Verzeichnisse.
Nutzt die Firecrawl API fuer JavaScript-Rendering und Anti-Bot-Schutz.

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

# ── Zu scrapende Seiten ──────────────────────────────────────────────────────

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


# ── FutureTools Parser ────────────────────────────────────────────────────────

def parse_futuretools_markdown(markdown: str) -> List[Dict]:
    """
    Parst die Markdown-Ausgabe von FutureTools (Homepage + Newly Added).

    Erkanntes Format:
      [![logo](img-url)](https://www.futuretools.io/tools/slug)
      [ToolName](https://www.futuretools.io/tools/slug)
      Beschreibungstext (eine Zeile)
      [Kategorie](https://www.futuretools.io/?tags=...)
    """
    tools = []
    lines = markdown.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Tool-Link erkennen: [Name](https://www.futuretools.io/tools/...)
        # Muss ein reiner Textlink sein (kein Bild-Link)
        tool_match = re.match(
            r"^\[([^\]!\[]+)\]\((https?://www\.futuretools\.io/tools/[^)]+)\)$",
            line,
        )
        if tool_match:
            name = tool_match.group(1).strip()
            tool_url = tool_match.group(2).strip()
            description = ""
            category = None

            # Naechste Zeilen nach Beschreibung und Kategorie durchsuchen
            j = i + 1
            while j < len(lines) and j < i + 8:
                next_line = lines[j].strip()
                if not next_line:
                    j += 1
                    continue

                # Kategorie-Link erkennen (verschiedene URL-Formate)
                cat_match = re.match(
                    r"^\[([^\]]+)\]\(https?://www\.futuretools\.io/\?tags",
                    next_line,
                )
                if cat_match:
                    category = cat_match.group(1).strip()
                    j += 1
                    continue

                # Upvote-Bilder und Navigationslinks ueberspringen
                if next_line.startswith("[![") or next_line.startswith("!["):
                    j += 1
                    continue

                # Reine Zahlen ueberspringen (Upvote-Counts)
                if re.match(r"^\d+\]?\(?", next_line):
                    j += 1
                    continue

                # Naechster Tool-Link? Aufhoeren
                if re.match(r"^\[([^\]!\[]+)\]\(https?://www\.futuretools\.io/tools/", next_line):
                    break

                # Naechstes Tool-Bild? Aufhoeren
                if re.match(r"^\[!\[", next_line):
                    break

                # Beschreibung (erste sinnvolle Textzeile, keine Links)
                if (
                    not description
                    and not next_line.startswith("[")
                    and not next_line.startswith("#")
                    and len(next_line) > 10
                ):
                    description = next_line

                j += 1

            # Nur echte Tools speichern (nicht Footer-Links, Navigation etc.)
            if name and len(name) < 100 and len(name) > 1:
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


# ── Futurepedia Parser ────────────────────────────────────────────────────────

def parse_futurepedia_category_markdown(markdown: str) -> List[Dict]:
    """
    Parst die Markdown-Ausgabe von Futurepedia Kategorie-Seiten.

    Erkanntes Format auf Kategorie-Seiten:
      [![ToolName logo](img-url)](https://www.futurepedia.io/tool/slug)
      [ToolName](https://www.futurepedia.io/tool/slug) [Rated X out of 5...](url)
      Free|Freemium|Paid + Zahl + "Add bookmark"
      Beschreibungstext (eine Zeile)
      [#kategorie1](url) [#kategorie2](url)
      Editor's Pick (optional)
      [Visit](external-url)
    """
    tools = []
    lines = markdown.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Tool-Link erkennen: [Name](https://www.futurepedia.io/tool/...)
        # Muss am Zeilenanfang stehen, kann von Rating-Link gefolgt werden
        tool_match = re.match(
            r"^\[([^\]]+)\]\((https?://www\.futurepedia\.io/tool/[^)]+)\)",
            line,
        )
        if tool_match:
            raw_name = tool_match.group(1).strip()
            tool_url = tool_match.group(2).strip()

            # "Rated X out of 5" als Name ausfiltern
            if "Rated" in raw_name and "out of" in raw_name:
                i += 1
                continue

            name = raw_name
            description = ""
            categories = []
            pricing = None
            visit_url = None

            # Naechste Zeilen durchsuchen
            j = i + 1
            while j < len(lines) and j < i + 15:
                next_line = lines[j].strip()
                if not next_line:
                    j += 1
                    continue

                # Rating-Link ueberspringen
                if "Rated" in next_line and "out of" in next_line:
                    j += 1
                    continue

                # Bild-Links ueberspringen
                if next_line.startswith("[![") or next_line.startswith("!["):
                    j += 1
                    continue

                # Naechster Tool-Link? Aufhoeren
                if re.match(
                    r"^\[!\[.*logo", next_line
                ) or re.match(
                    r"^\[([^\]]+)\]\(https?://www\.futurepedia\.io/tool/", next_line
                ):
                    # Pruefen ob es nicht der Rating-Link ist
                    rating_check = re.match(
                        r"^\[Rated", next_line
                    )
                    if not rating_check:
                        break

                # Pricing erkennen: "Free78Add bookmark", "Freemium1239Add bookmark"
                pricing_match = re.match(
                    r"^(Free|Freemium|Paid)\d*Add bookmark",
                    next_line,
                    re.IGNORECASE,
                )
                if pricing_match:
                    pricing = pricing_match.group(1).lower()
                    j += 1
                    continue

                # Auch einfaches Format: "Free", "Freemium", "Paid" am Zeilenanfang
                if re.match(r"^(Free|Freemium|Paid)\b", next_line, re.IGNORECASE):
                    pricing = next_line.split()[0].lower()
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

                # Visit-Link (externe URL des Tools)
                visit_match = re.match(
                    r"^\[Visit\]\((https?://[^)]+)\)",
                    next_line,
                )
                if visit_match:
                    visit_url = visit_match.group(1).strip()
                    j += 1
                    continue

                # "Editor's Pick" ueberspringen
                if next_line.lower() == "editor's pick":
                    j += 1
                    continue

                # "Previous slide", "Next slide" ueberspringen
                if next_line.lower() in ("previous slide", "next slide"):
                    j += 1
                    continue

                # Duplikat-Name ueberspringen
                if next_line == name:
                    j += 1
                    continue

                # Reine Zahlen ueberspringen (Bewertungsanzahl)
                if re.match(r"^\(\d+\)$", next_line) or re.match(r"^\d+$", next_line):
                    j += 1
                    continue

                # Rating-Fragmente ueberspringen: "(7)](url)" oder "\\\n(7)" etc.
                if re.match(r"^\(?\d+\)?\]", next_line):
                    j += 1
                    continue
                if re.match(r"^\\$", next_line) or re.match(r"^\\\\$", next_line):
                    j += 1
                    continue

                # Beschreibung (erste sinnvolle Textzeile)
                if (
                    not description
                    and not next_line.startswith("[")
                    and not next_line.startswith("#")
                    and len(next_line) > 10
                    and "Add bookmark" not in next_line
                    and not re.match(r"^\(?\d+\)?(\]|\))", next_line)
                    and "futurepedia.io" not in next_line
                ):
                    description = next_line

                j += 1

            # Kategorie als komma-getrennte Liste
            category_str = ", ".join(categories[:3]) if categories else None

            # Nur echte Tools speichern
            if (
                name
                and len(name) < 100
                and len(name) > 1
                and "cookie" not in name.lower()
                and "Rated" not in name
            ):
                tools.append({
                    "name": name,
                    "url": tool_url,
                    "description": description,
                    "category": category_str,
                    "pricing": pricing,
                    "visit_url": visit_url,
                    "source": "futurepedia",
                })
            i = j if j > i + 1 else i + 1
        else:
            i += 1

    return tools


def parse_futurepedia_homepage_markdown(markdown: str) -> List[Dict]:
    """
    Parst die Markdown-Ausgabe der Futurepedia-Startseite.

    Format auf der Homepage:
      [ToolName](https://www.futurepedia.io/tool/slug)
      ToolName (Wiederholung)
      Beschreibungstext
      [#kategorie](url)
    """
    tools = []
    lines = markdown.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Tool-Link erkennen
        tool_match = re.match(
            r"^\[([^\]]+)\]\((https?://www\.futurepedia\.io/tool/[^)]+)\)",
            line,
        )
        if tool_match:
            raw_name = tool_match.group(1).strip()
            tool_url = tool_match.group(2).strip()

            # Rating-Links ueberspringen
            if "Rated" in raw_name and "out of" in raw_name:
                i += 1
                continue

            name = raw_name
            description = ""
            categories = []

            j = i + 1
            while j < len(lines) and j < i + 10:
                next_line = lines[j].strip()
                if not next_line:
                    j += 1
                    continue

                # Duplikat-Name ueberspringen
                if next_line == name:
                    j += 1
                    continue

                # Reine Zahlen ueberspringen
                if re.match(r"^\d+$", next_line):
                    j += 1
                    continue

                # Rating ueberspringen
                if "Rated" in next_line and "out of" in next_line:
                    j += 1
                    continue

                # Bild-Links ueberspringen
                if next_line.startswith("[![") or next_line.startswith("!["):
                    j += 1
                    continue

                # Naechster Tool-Link? Aufhoeren
                if re.match(r"\[([^\]]+)\]\(https?://www\.futurepedia\.io/tool/", next_line):
                    if "Rated" not in next_line:
                        break

                # Kategorie-Tags
                cat_matches = re.findall(
                    r"\[#([^\]]+)\]\(https?://www\.futurepedia\.io/ai-tools/[^)]+\)",
                    next_line,
                )
                if cat_matches:
                    categories.extend(cat_matches)
                    j += 1
                    continue

                # Beschreibung
                if (
                    not description
                    and not next_line.startswith("[")
                    and not next_line.startswith("#")
                    and len(next_line) > 10
                ):
                    description = next_line

                j += 1

            category_str = ", ".join(categories[:3]) if categories else None

            if (
                name
                and len(name) < 100
                and len(name) > 1
                and "cookie" not in name.lower()
                and "Rated" not in name
            ):
                tools.append({
                    "name": name,
                    "url": tool_url,
                    "description": description,
                    "category": category_str,
                    "pricing": None,
                    "visit_url": None,
                    "source": "futurepedia",
                })
            i = j if j > i + 1 else i + 1
        else:
            i += 1

    return tools


# ── Scraping-Logik ────────────────────────────────────────────────────────────

def _scrape_url(client: FirecrawlApp, url: str) -> str:
    """Scrapt eine URL mit Firecrawl und gibt den Markdown-Inhalt zurueck."""
    try:
        result = client.scrape_url(url, params={"formats": ["markdown"]})
        return result.get("markdown", "")
    except Exception as e:
        logger.warning(f"Firecrawl-Scrape fehlgeschlagen fuer {url}: {e}")
        return ""


def _save_tools(tools: List[Dict], source: str, db: Session) -> int:
    """Speichert Tools in die Datenbank. Gibt Anzahl neuer/aktualisierter Eintraege zurueck."""
    new_count = 0
    for tool in tools:
        if not tool.get("name") or not tool.get("url"):
            continue

        # Beschreibung kuerzen falls zu lang
        description = tool.get("description", "")
        if description and len(description) > 2000:
            description = description[:2000] + "..."

        tool_url = tool.get("url", "")

        # Upsert: neues Tool einfuegen oder vorhandenes aktualisieren
        # Aktualisiert Beschreibung/Pricing/Kategorie nur wenn neue Werte vorhanden
        stmt = pg_insert(AiTools).values(
            name=tool["name"][:200],
            description=description,
            url=tool_url,
            pricing=tool.get("pricing"),
            category=tool.get("category"),
            source=source,
        ).on_conflict_do_update(
            index_elements=["url"],
            set_={
                "description": description if description else AiTools.description,
                "pricing": tool.get("pricing") if tool.get("pricing") else AiTools.pricing,
                "category": tool.get("category") if tool.get("category") else AiTools.category,
            },
        )

        result = db.execute(stmt)
        if result.rowcount > 0:
            new_count += 1

    db.commit()
    return new_count


def scrape_futuretools(client: FirecrawlApp, db: Session) -> int:
    """
    Scrapt alle FutureTools-Seiten (Homepage + Newly Added).
    Gibt die Gesamtanzahl neuer/aktualisierter Tools zurueck.
    """
    total = 0

    for url in FUTURETOOLS_URLS:
        try:
            logger.info(f"Scrape FutureTools: {url}")
            markdown = _scrape_url(client, url)
            if not markdown:
                continue

            logger.info(f"FutureTools {url}: {len(markdown)} Zeichen Markdown erhalten")
            tools = parse_futuretools_markdown(markdown)
            logger.info(f"FutureTools {url}: {len(tools)} Tools gefunden")

            count = _save_tools(tools, "futuretools", db)
            total += count
            logger.info(f"FutureTools {url}: {count} neue/aktualisierte Tools gespeichert")

            time.sleep(SCRAPE_DELAY)
        except Exception as e:
            logger.error(f"Fehler bei FutureTools {url}: {e}")
            db.rollback()
            continue

    return total


def scrape_futurepedia(client: FirecrawlApp, db: Session) -> int:
    """
    Scrapt Futurepedia Homepage + alle konfigurierten Kategorie-Seiten.
    Gibt die Gesamtanzahl neuer/aktualisierter Tools zurueck.
    """
    total = 0

    # Zuerst die Homepage
    for url in FUTUREPEDIA_EXTRA_URLS:
        try:
            logger.info(f"Scrape Futurepedia Homepage: {url}")
            markdown = _scrape_url(client, url)
            if not markdown:
                continue

            logger.info(f"Futurepedia Homepage: {len(markdown)} Zeichen Markdown erhalten")
            tools = parse_futurepedia_homepage_markdown(markdown)
            logger.info(f"Futurepedia Homepage: {len(tools)} Tools gefunden")

            count = _save_tools(tools, "futurepedia", db)
            total += count
            logger.info(f"Futurepedia Homepage: {count} neue/aktualisierte Tools gespeichert")

            time.sleep(SCRAPE_DELAY)
        except Exception as e:
            logger.error(f"Fehler bei Futurepedia Homepage {url}: {e}")
            db.rollback()
            continue

    # Dann die Kategorie-Seiten
    for url in FUTUREPEDIA_CATEGORY_URLS:
        try:
            category_name = url.split("/")[-1]
            logger.info(f"Scrape Futurepedia Kategorie: {category_name} ({url})")
            markdown = _scrape_url(client, url)
            if not markdown:
                continue

            logger.info(f"Futurepedia {category_name}: {len(markdown)} Zeichen Markdown erhalten")
            tools = parse_futurepedia_category_markdown(markdown)
            logger.info(f"Futurepedia {category_name}: {len(tools)} Tools gefunden")

            count = _save_tools(tools, "futurepedia", db)
            total += count
            logger.info(f"Futurepedia {category_name}: {count} neue/aktualisierte Tools gespeichert")

            time.sleep(SCRAPE_DELAY)
        except Exception as e:
            logger.error(f"Fehler bei Futurepedia {url}: {e}")
            db.rollback()
            continue

    return total


# ── Legacy-Kompatibilitaet ────────────────────────────────────────────────────

def parse_tools_from_markdown(markdown: str, source: str) -> List[Dict]:
    """Waehlt den richtigen Parser basierend auf der Quelle (Legacy-Kompatibilitaet)."""
    if source == "futuretools":
        return parse_futuretools_markdown(markdown)
    elif source == "futurepedia":
        return parse_futurepedia_category_markdown(markdown)
    return []


def scrape_single_target(target: Dict, client: FirecrawlApp, db: Session) -> int:
    """Legacy-Funktion — wird nicht mehr direkt verwendet."""
    return 0


# ── Hauptfunktion ─────────────────────────────────────────────────────────────

def scrape_all_tools(db: Session) -> int:
    """
    Scrapt alle konfigurierten Tool-Verzeichnisse.
    FutureTools: Homepage + Newly Added (~20-30 Tools)
    Futurepedia: Homepage + 15 Kategorie-Seiten (~200+ Tools)

    Fehler bei einer Seite stoppen nicht die anderen.
    Gibt die Gesamtanzahl neu gespeicherter/aktualisierter Eintraege zurueck.
    """
    client = get_firecrawl_client()
    if not client:
        logger.error("Firecrawl-Client konnte nicht erstellt werden.")
        return 0

    total_new = 0
    logger.info("Starte erweitertes Firecrawl-Scraping (FutureTools + Futurepedia Kategorien)...")

    # FutureTools scrapen
    try:
        ft_count = scrape_futuretools(client, db)
        total_new += ft_count
        logger.info(f"FutureTools fertig: {ft_count} neue/aktualisierte Tools")
    except Exception as e:
        logger.error(f"Unerwarteter Fehler bei FutureTools: {e}")

    # Futurepedia scrapen (Homepage + Kategorien)
    try:
        fp_count = scrape_futurepedia(client, db)
        total_new += fp_count
        logger.info(f"Futurepedia fertig: {fp_count} neue/aktualisierte Tools")
    except Exception as e:
        logger.error(f"Unerwarteter Fehler bei Futurepedia: {e}")

    logger.info(f"Firecrawl-Scraping abgeschlossen. Insgesamt {total_new} neue/aktualisierte Tools.")
    return total_new

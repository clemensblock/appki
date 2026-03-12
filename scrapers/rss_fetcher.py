"""
RSS-Fetcher fuer KI-News aus verschiedenen Quellen.
Nutzt feedparser — kein Firecrawl noetig, RSS ist direkt kostenlos.
Laeuft alle 2 Stunden fuer maximale Aktualitaet.
"""

import re
import logging
from datetime import datetime, timezone
from typing import List, Dict

import feedparser
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from models import AiNews

logger = logging.getLogger(__name__)

# Konfiguration der RSS-Feeds mit differenzierten Kategorien
RSS_FEEDS: List[Dict[str, str]] = [
    # Grosse Tech-News-Portale
    {
        "name": "techcrunch",
        "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "category": "industry",
    },
    {
        "name": "venturebeat",
        "url": "https://venturebeat.com/ai/feed/",
        "category": "enterprise",
    },
    {
        "name": "the-verge",
        "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "category": "industry",
    },
    {
        "name": "ars-technica",
        "url": "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "category": "research",
    },
    {
        "name": "wired",
        "url": "https://www.wired.com/feed/tag/ai/latest/rss",
        "category": "industry",
    },
    # KI-spezifische Quellen
    {
        "name": "ai-news",
        "url": "https://www.artificialintelligence-news.com/feed/",
        "category": "research",
    },
    {
        "name": "therundown",
        "url": "https://rss.beehiiv.com/feeds/2R3C6Bxd1D",
        "category": "newsletter",
    },
    # Hersteller-Blogs
    {
        "name": "openai",
        "url": "https://openai.com/news/rss.xml",
        "category": "releases",
    },
    {
        "name": "google-ai",
        "url": "https://blog.google/technology/ai/rss/",
        "category": "releases",
    },
    {
        "name": "huggingface",
        "url": "https://huggingface.co/blog/feed.xml",
        "category": "research",
    },
    # Forschung
    {
        "name": "mit-tech-review",
        "url": "https://www.technologyreview.com/feed/",
        "category": "research",
    },
]


def _strip_html(text: str) -> str:
    """Entfernt HTML-Tags und bereinigt den Text."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", "", text)
    clean = clean.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    clean = clean.replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def parse_published_date(entry) -> datetime | None:
    """Versucht, das Veroeffentlichungsdatum aus einem Feed-Eintrag zu extrahieren."""
    published = entry.get("published_parsed") or entry.get("updated_parsed")
    if published:
        try:
            return datetime(*published[:6], tzinfo=timezone.utc)
        except Exception:
            pass
    return None


def fetch_single_feed(feed_config: Dict[str, str], db: Session) -> int:
    """
    Ruft einen einzelnen RSS-Feed ab und speichert neue Eintraege.
    HTML wird aus Zusammenfassungen entfernt.
    Deduplizierung per URL.
    """
    feed_name = feed_config["name"]
    feed_url = feed_config["url"]
    category = feed_config["category"]
    new_count = 0

    try:
        logger.info(f"Rufe RSS-Feed ab: {feed_name} ({feed_url})")
        feed = feedparser.parse(feed_url)

        if feed.bozo and not feed.entries:
            logger.warning(f"Feed {feed_name} hat Fehler: {feed.bozo_exception}")
            return 0

        for entry in feed.entries:
            title = entry.get("title", "").strip()
            url = entry.get("link", "").strip()
            raw_summary = entry.get("summary", "").strip()

            if not title or not url:
                continue

            # HTML aus Zusammenfassung entfernen
            summary = _strip_html(raw_summary)
            if summary and len(summary) > 2000:
                summary = summary[:2000] + "..."

            published_at = parse_published_date(entry)

            stmt = pg_insert(AiNews).values(
                title=title,
                url=url,
                summary=summary,
                source=feed_name,
                category=category,
                published_at=published_at,
            ).on_conflict_do_nothing(index_elements=["url"])

            result = db.execute(stmt)
            if result.rowcount > 0:
                new_count += 1

        db.commit()
        logger.info(f"Feed {feed_name}: {new_count} neue Eintraege gespeichert")

    except Exception as e:
        logger.error(f"Fehler beim Abrufen von Feed {feed_name}: {e}")
        db.rollback()

    return new_count


def fetch_all_rss_feeds(db: Session) -> int:
    """
    Ruft alle konfigurierten RSS-Feeds ab.
    Fehler bei einem Feed stoppen nicht die anderen.
    """
    total_new = 0
    logger.info(f"Starte RSS-Feed-Abruf fuer {len(RSS_FEEDS)} Quellen...")

    for feed_config in RSS_FEEDS:
        try:
            count = fetch_single_feed(feed_config, db)
            total_new += count
        except Exception as e:
            logger.error(f"Unerwarteter Fehler bei Feed {feed_config['name']}: {e}")
            continue

    logger.info(f"RSS-Abruf abgeschlossen. Insgesamt {total_new} neue Eintraege.")
    return total_new

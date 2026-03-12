"""
APScheduler-Konfiguration für automatische Scraping-Jobs.
Läuft direkt in FastAPI als AsyncIOScheduler.
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database import SessionLocal
from scrapers.rss_fetcher import fetch_all_rss_feeds
from scrapers.firecrawl_scraper import scrape_all_tools

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def job_fetch_rss():
    """Täglicher Job: Alle RSS-Feeds abrufen (06:00 Uhr)."""
    logger.info("=== Scheduler-Job gestartet: RSS-Feed-Abruf ===")
    db = SessionLocal()
    try:
        count = fetch_all_rss_feeds(db)
        logger.info(f"=== RSS-Job abgeschlossen: {count} neue Einträge ===")
    except Exception as e:
        logger.error(f"RSS-Job Fehler: {e}")
    finally:
        db.close()


def job_scrape_tools():
    """Täglicher Job: Tool-Verzeichnisse scrapen (07:00 Uhr)."""
    logger.info("=== Scheduler-Job gestartet: Tool-Scraping ===")
    db = SessionLocal()
    try:
        count = scrape_all_tools(db)
        logger.info(f"=== Scraping-Job abgeschlossen: {count} neue Tools ===")
    except Exception as e:
        logger.error(f"Scraping-Job Fehler: {e}")
    finally:
        db.close()


def start_scheduler():
    """Startet den Scheduler mit allen konfigurierten Jobs."""
    # RSS-Feeds täglich um 06:00 Uhr abrufen
    scheduler.add_job(
        job_fetch_rss,
        trigger=CronTrigger(hour=6, minute=0),
        id="fetch_rss",
        name="RSS-Feed-Abruf",
        replace_existing=True,
    )

    # Tool-Verzeichnisse täglich um 07:00 Uhr scrapen
    scheduler.add_job(
        job_scrape_tools,
        trigger=CronTrigger(hour=7, minute=0),
        id="scrape_tools",
        name="Tool-Scraping",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler gestartet mit Jobs: fetch_rss (06:00), scrape_tools (07:00)")


def stop_scheduler():
    """Beendet den Scheduler sauber."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler beendet.")

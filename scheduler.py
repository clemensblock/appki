"""
APScheduler-Konfiguration für automatische Scraping-Jobs.
Läuft direkt in FastAPI als AsyncIOScheduler.

3 Jobs:
  06:00 — RSS-Feeds abrufen
  07:00 — Collector (Stufe 1): Tool-Namen und URLs sammeln
  08:00 — Enrichment Agent (Stufe 2): Details fuer pending Tools nachladen
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database import SessionLocal
from scrapers.rss_fetcher import fetch_all_rss_feeds
from scrapers.firecrawl_scraper import collect_all_tools
from scrapers.enrichment_agent import enrich_pending_tools

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


def job_collect_tools():
    """Täglicher Job: Tool-Namen und URLs sammeln (07:00 Uhr) — Stufe 1."""
    logger.info("=== Scheduler-Job gestartet: Collector (Stufe 1) ===")
    db = SessionLocal()
    try:
        count = collect_all_tools(db)
        logger.info(f"=== Collector-Job abgeschlossen: {count} neue Tools gesammelt ===")
    except Exception as e:
        logger.error(f"Collector-Job Fehler: {e}")
    finally:
        db.close()


def job_enrich_tools():
    """Täglicher Job: Details fuer pending Tools nachladen (08:00 Uhr) — Stufe 2."""
    logger.info("=== Scheduler-Job gestartet: Enrichment Agent (Stufe 2) ===")
    db = SessionLocal()
    try:
        result = enrich_pending_tools(db)
        logger.info(f"=== Enrichment-Job abgeschlossen: {result} ===")
    except Exception as e:
        logger.error(f"Enrichment-Job Fehler: {e}")
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

    # Collector (Stufe 1): Tool-Namen und URLs sammeln um 07:00 Uhr
    scheduler.add_job(
        job_collect_tools,
        trigger=CronTrigger(hour=7, minute=0),
        id="collect_tools",
        name="Tool-Collector (Stufe 1)",
        replace_existing=True,
    )

    # Enrichment Agent (Stufe 2): Details nachladen um 08:00 Uhr
    scheduler.add_job(
        job_enrich_tools,
        trigger=CronTrigger(hour=8, minute=0),
        id="enrich_tools",
        name="Enrichment-Agent (Stufe 2)",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "Scheduler gestartet mit Jobs: "
        "fetch_rss (06:00), collect_tools (07:00), enrich_tools (08:00)"
    )


def stop_scheduler():
    """Beendet den Scheduler sauber."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler beendet.")

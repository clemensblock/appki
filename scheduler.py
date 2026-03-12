"""
APScheduler-Konfiguration fuer automatische Scraping-Jobs.
Laeuft direkt in FastAPI als AsyncIOScheduler.

Jobs:
  Alle 2h  — RSS-Feeds abrufen (06:00, 08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00)
  07:00    — Collector (Stufe 1): Tool-Namen und URLs sammeln
  08:00    — Enrichment Agent (Stufe 2): Details fuer pending Tools nachladen
  08:30    — News Enrichment: Uebersetzung und Zusammenfassung auf Deutsch
  09:00    — Retry fehlgeschlagener Tools
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database import SessionLocal
from scrapers.rss_fetcher import fetch_all_rss_feeds
from scrapers.firecrawl_scraper import collect_all_tools
from scrapers.enrichment_agent import enrich_pending_tools, retry_failed_tools
from scrapers.news_enrichment import enrich_pending_news

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def job_fetch_rss():
    """Job: Alle RSS-Feeds abrufen (alle 2 Stunden)."""
    logger.info("=== Scheduler-Job gestartet: RSS-Feed-Abruf ===")
    db = SessionLocal()
    try:
        count = fetch_all_rss_feeds(db)
        logger.info(f"=== RSS-Job abgeschlossen: {count} neue Eintraege ===")
    except Exception as e:
        logger.error(f"RSS-Job Fehler: {e}")
    finally:
        db.close()


def job_collect_tools():
    """Taeglicher Job: Tool-Namen und URLs sammeln (07:00 Uhr) — Stufe 1."""
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
    """Taeglicher Job: Details fuer pending Tools nachladen (08:00 Uhr) — Stufe 2."""
    logger.info("=== Scheduler-Job gestartet: Enrichment Agent (Stufe 2) ===")
    db = SessionLocal()
    try:
        result = enrich_pending_tools(db)
        logger.info(f"=== Enrichment-Job abgeschlossen: {result} ===")
    except Exception as e:
        logger.error(f"Enrichment-Job Fehler: {e}")
    finally:
        db.close()


def job_enrich_news():
    """Job: News auf Deutsch uebersetzen und zusammenfassen (08:30 Uhr)."""
    logger.info("=== Scheduler-Job gestartet: News-Enrichment ===")
    db = SessionLocal()
    try:
        result = enrich_pending_news(db)
        logger.info(f"=== News-Enrichment-Job abgeschlossen: {result} ===")
    except Exception as e:
        logger.error(f"News-Enrichment-Job Fehler: {e}")
    finally:
        db.close()


def job_retry_tools():
    """Taeglicher Job: Fehlgeschlagene Tools erneut versuchen (09:00 Uhr)."""
    logger.info("=== Scheduler-Job gestartet: Retry fehlgeschlagener Tools ===")
    db = SessionLocal()
    try:
        result = retry_failed_tools(db)
        logger.info(f"=== Retry-Job abgeschlossen: {result} ===")
    except Exception as e:
        logger.error(f"Retry-Job Fehler: {e}")
    finally:
        db.close()


def start_scheduler():
    """Startet den Scheduler mit allen konfigurierten Jobs."""
    # RSS-Feeds alle 2 Stunden abrufen (kostenlos, maximale Aktualitaet)
    scheduler.add_job(
        job_fetch_rss,
        trigger=CronTrigger(hour="6,8,10,12,14,16,18,20", minute=0),
        id="fetch_rss",
        name="RSS-Feed-Abruf (alle 2h)",
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

    # News-Enrichment: Uebersetzung und Zusammenfassung um 08:30 Uhr
    scheduler.add_job(
        job_enrich_news,
        trigger=CronTrigger(hour="6,8,10,12,14,16,18,20", minute=30),
        id="enrich_news",
        name="News-Enrichment (Deutsch)",
        replace_existing=True,
    )

    # Retry fehlgeschlagener Tools um 09:00 Uhr
    scheduler.add_job(
        job_retry_tools,
        trigger=CronTrigger(hour=9, minute=0),
        id="retry_tools",
        name="Retry fehlgeschlagener Tools",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "Scheduler gestartet mit Jobs: "
        "fetch_rss (alle 2h), collect_tools (07:00), enrich_tools (08:00), "
        "enrich_news (alle 2h +30min), retry_tools (09:00)"
    )


def stop_scheduler():
    """Beendet den Scheduler sauber."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler beendet.")

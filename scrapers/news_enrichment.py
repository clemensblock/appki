"""
News Enrichment Agent fuer app.ki.

Uebersetzt und fasst News-Artikel auf Deutsch zusammen via OpenAI API.
Erstellt eigenstaendige, professionelle deutsche Texte (keine 1:1 Uebersetzung).

Status-Uebergaenge:
  'pending' -> 'done'   (erfolgreich uebersetzt und zusammengefasst)
  'pending' -> 'error'  (Fehler bei der Verarbeitung)
"""

import os
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy.orm import Session
from sqlalchemy import text

from models import AiNews

logger = logging.getLogger(__name__)

NEWS_ENRICHMENT_BATCH_SIZE = int(os.getenv("NEWS_ENRICHMENT_BATCH_SIZE", "30"))
ENRICHMENT_DELAY = 0.5  # Sekunden zwischen API-Calls

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-4o-mini"

TRANSLATION_PROMPT = """Du bist ein professioneller deutscher Tech-Journalist fuer eine fuehrende KI-Informationsplattform.

Aufgabe: Uebersetze und formuliere den folgenden englischen News-Artikel eigenstaendig auf Deutsch um.
Erstelle KEINEN 1:1 uebersetzten Text, sondern formuliere einen eigenstaendigen, professionellen deutschen Artikel.

Gib das Ergebnis als JSON zurueck mit genau diesen Feldern:
- "title_de": Praegnante deutsche Ueberschrift (max 120 Zeichen)
- "summary_de": Professionelle deutsche Zusammenfassung in 3-5 Saetzen. Erklaere das Wichtigste verstaendlich fuer ein deutschsprachiges Fachpublikum.

WICHTIG:
- Schreibe professionell, nicht werblich
- Verwende gaengige deutsche Fachbegriffe (z.B. "Kuenstliche Intelligenz" statt "Artificial Intelligence")
- Englische Produktnamen und Eigennamen bleiben auf Englisch
- Antworte NUR mit validem JSON, kein Text drumherum
"""


def _get_openai_key() -> Optional[str]:
    """Liest den OpenAI API Key aus der Umgebung."""
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        logger.error("OPENAI_API_KEY ist nicht gesetzt!")
        return None
    return key


def _translate_with_openai(title: str, summary: str, openai_key: str) -> Optional[dict]:
    """
    Uebersetzt und fasst einen News-Artikel via OpenAI API zusammen.
    Gibt ein Dict mit title_de und summary_de zurueck.
    """
    try:
        headers = {
            "Authorization": f"Bearer {openai_key}",
            "Content-Type": "application/json",
        }

        user_content = f"Titel: {title}\n\nZusammenfassung: {summary or 'Keine Zusammenfassung vorhanden.'}"

        payload = {
            "model": OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": TRANSLATION_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": 500,
            "temperature": 0.3,
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(OPENAI_API_URL, json=payload, headers=headers)
            response.raise_for_status()

        result = response.json()
        content_text = result["choices"][0]["message"]["content"].strip()

        # JSON aus Antwort extrahieren (Code-Block-Handling)
        if content_text.startswith("```"):
            lines = content_text.split("\n")
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
            content_text = "\n".join(json_lines)

        data = json.loads(content_text)
        return data

    except json.JSONDecodeError as e:
        logger.warning(f"News-Enrichment: JSON-Parse-Fehler: {e}")
        return None
    except httpx.HTTPStatusError as e:
        logger.warning(f"News-Enrichment: OpenAI API HTTP-Fehler: {e}")
        return None
    except Exception as e:
        logger.warning(f"News-Enrichment: Unerwarteter Fehler: {e}")
        return None


def _update_news(db: Session, news_id: int, data: dict) -> None:
    """Aktualisiert einen News-Artikel mit der deutschen Uebersetzung."""
    title_de = data.get("title_de", "")
    if title_de and len(title_de) > 500:
        title_de = title_de[:500]

    summary_de = data.get("summary_de", "")
    if summary_de and len(summary_de) > 3000:
        summary_de = summary_de[:3000]

    db.execute(
        text("""
            UPDATE ai_news SET
                title_de = :title_de,
                summary_de = :summary_de,
                enrichment_status = 'done',
                enriched_at = :enriched_at
            WHERE id = :news_id
        """),
        {
            "title_de": title_de or None,
            "summary_de": summary_de or None,
            "enriched_at": datetime.now(timezone.utc),
            "news_id": news_id,
        },
    )
    db.commit()


def _mark_news_error(db: Session, news_id: int) -> None:
    """Setzt den Enrichment-Status eines News-Artikels auf 'error'."""
    db.execute(
        text("UPDATE ai_news SET enrichment_status = 'error' WHERE id = :news_id"),
        {"news_id": news_id},
    )
    db.commit()


def enrich_pending_news(db: Session) -> dict:
    """
    News Enrichment Agent: Uebersetzt und fasst alle pending News auf Deutsch zusammen.

    Gibt ein Dict mit Statistiken zurueck:
      {"enriched": N, "errors": M}
    """
    openai_key = _get_openai_key()
    if not openai_key:
        return {"enriched": 0, "errors": 0, "error": "OPENAI_API_KEY fehlt"}

    # Pending News laden (neueste zuerst, limitiert auf Batch-Groesse)
    pending_news = (
        db.query(AiNews)
        .filter(AiNews.enrichment_status == "pending")
        .order_by(AiNews.fetched_at.desc())
        .limit(NEWS_ENRICHMENT_BATCH_SIZE)
        .all()
    )

    if not pending_news:
        logger.info("News-Enrichment: Keine pending News vorhanden.")
        return {"enriched": 0, "errors": 0}

    logger.info(f"=== News-Enrichment gestartet: {len(pending_news)} Artikel zu verarbeiten ===")

    enriched = 0
    errors = 0

    for news in pending_news:
        try:
            logger.info(f"News-Enrichment: Verarbeite '{news.title[:60]}...'")

            data = _translate_with_openai(news.title, news.summary or "", openai_key)
            if not data:
                logger.warning(f"News-Enrichment: Fehler bei '{news.title[:60]}...'")
                _mark_news_error(db, news.id)
                errors += 1
                time.sleep(ENRICHMENT_DELAY)
                continue

            _update_news(db, news.id, data)
            enriched += 1
            logger.info(f"News-Enrichment: '{data.get('title_de', '')[:60]}...' erfolgreich")

        except Exception as e:
            logger.error(f"News-Enrichment: Unerwarteter Fehler bei ID {news.id}: {e}")
            try:
                _mark_news_error(db, news.id)
            except Exception:
                db.rollback()
            errors += 1

        time.sleep(ENRICHMENT_DELAY)

    logger.info(f"=== News-Enrichment abgeschlossen: {enriched} uebersetzt, {errors} Fehler ===")
    return {"enriched": enriched, "errors": errors}

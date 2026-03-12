# app.ki

Plattform fuer die neuesten KI-Tools und KI-News, automatisch gesammelt aus amerikanischen Quellen.

## Tech Stack

- **Backend**: FastAPI + Uvicorn
- **Datenbank**: PostgreSQL 16
- **Scraping**: Firecrawl API + RSS (feedparser)
- **Scheduler**: APScheduler
- **Webserver**: Nginx als Reverse Proxy
- **SSL**: Let's Encrypt via Certbot
- **Deployment**: systemd Services auf Ubuntu 24.04

## Schnellstart

### 1. Repository klonen
```bash
cd /opt
git clone https://github.com/clemensblock/appki.git appki
cd appki
```

### 2. Umgebungsvariablen konfigurieren
```bash
cp .env.example .env
nano .env  # Echte Werte eintragen
```

### 3. Installation ausfuehren
```bash
chmod +x install.sh
./install.sh
```

### 4. SSL-Zertifikat einrichten (optional)
```bash
certbot --nginx -d dev.app.ki
```

## API Endpoints

| Endpoint | Methode | Beschreibung |
|---|---|---|
| `/` | GET | Webseite mit News & Tools |
| `/api/status` | GET | Status und Version |
| `/api/stats` | GET | Anzahl News und Tools |
| `/api/news` | GET | News-Liste (filter: source, category, limit, offset) |
| `/api/news/{id}` | GET | Einzelner News-Eintrag |
| `/api/news/sources` | GET | Verfuegbare Quellen |
| `/api/tools` | GET | Tools-Liste (filter: source, category, pricing, limit, offset) |
| `/api/tools/{id}` | GET | Einzelnes Tool |
| `/api/tools/categories` | GET | Tool-Kategorien |
| `/api/admin/fetch-now` | POST | Alle Scraper sofort starten |
| `/docs` | GET | Swagger UI (automatisch) |

## Scraping-Quellen

### RSS-Feeds (taeglich 06:00 Uhr)
- TechCrunch AI
- VentureBeat AI
- The Rundown AI
- AI News
- OpenAI News

### Firecrawl Scraping (taeglich 07:00 Uhr)
- FutureTools (neue Tools)
- Futurepedia (KI-Tool-Verzeichnis)

## Verwaltung

```bash
# Service-Status
systemctl status appki

# Logs anzeigen
journalctl -u appki -f

# Service neustarten
systemctl restart appki

# Manuell Scraper starten
curl -X POST http://localhost/api/admin/fetch-now
```

## Projektstruktur

```
/opt/appki/
├── main.py              # FastAPI App + Frontend
├── database.py          # DB Connection
├── models.py            # SQLAlchemy Models
├── schemas.py           # Pydantic Schemas
├── scheduler.py         # APScheduler Jobs
├── requirements.txt
├── .env                 # Secrets (nicht im Git)
├── .env.example
├── appki.service        # systemd Service
├── nginx.conf           # Nginx Konfiguration
├── install.sh           # Installations-Script
├── routers/
│   ├── news.py          # /api/news Endpoints
│   └── tools.py         # /api/tools Endpoints
└── scrapers/
    ├── rss_fetcher.py   # RSS-Feed Abruf
    └── firecrawl_scraper.py  # Firecrawl Scraping
```

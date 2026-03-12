"""
app.ki — Hauptanwendung (FastAPI)
Plattform für KI-News und KI-Tools, automatisch gesammelt aus amerikanischen Quellen.
"""

import os
import secrets
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from dotenv import load_dotenv

load_dotenv()

from database import engine, get_db, Base
from models import AiNews, AiTools
from schemas import StatsResponse, StatusResponse
from routers import news, tools
from scheduler import start_scheduler, stop_scheduler
from scrapers.rss_fetcher import fetch_all_rss_feeds
from scrapers.firecrawl_scraper import collect_all_tools
from scrapers.enrichment_agent import enrich_pending_tools
from database import SessionLocal

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Passwortschutz — einfache HTTP Basic Auth fuer Entwicklung
SITE_USERNAME = os.getenv("SITE_USERNAME", "admin")
SITE_PASSWORD = os.getenv("SITE_PASSWORD", "appki2026!")
security = HTTPBasic()


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """Prueft HTTP Basic Auth Zugangsdaten."""
    correct_user = secrets.compare_digest(credentials.username.encode(), SITE_USERNAME.encode())
    correct_pass = secrets.compare_digest(credentials.password.encode(), SITE_PASSWORD.encode())
    if not (correct_user and correct_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Zugang verweigert",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle-Management: Tabellen anlegen und Scheduler starten."""
    # Startup
    logger.info("app.ki startet — Tabellen werden angelegt...")
    Base.metadata.create_all(bind=engine)
    logger.info("Datenbank-Tabellen bereit.")

    start_scheduler()
    logger.info("app.ki ist bereit.")

    yield

    # Shutdown
    logger.info("app.ki wird heruntergefahren...")
    stop_scheduler()
    logger.info("app.ki beendet.")


app = FastAPI(
    title="app.ki",
    description="Plattform für die neuesten KI-Tools und KI-News — automatisch gesammelt aus amerikanischen Quellen.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS-Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router einbinden
app.include_router(news.router)
app.include_router(tools.router)


# --- Statische Seiten ---

FRONTEND_HTML = """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>app.ki — KI-News & Tools</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0a0a0f;
            --bg-secondary: #12121a;
            --bg-card: #1a1a2e;
            --bg-card-hover: #22223a;
            --accent: #6c63ff;
            --accent-light: #8b83ff;
            --accent-glow: rgba(108, 99, 255, 0.3);
            --text-primary: #f0f0f5;
            --text-secondary: #a0a0b5;
            --text-muted: #6a6a80;
            --border: #2a2a3e;
            --success: #4ade80;
            --warning: #fbbf24;
            --gradient-1: linear-gradient(135deg, #6c63ff 0%, #e040fb 100%);
            --gradient-2: linear-gradient(135deg, #00d2ff 0%, #6c63ff 100%);
            --gradient-3: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            overflow-x: hidden;
        }

        /* Animierter Hintergrund */
        .bg-gradient {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background:
                radial-gradient(ellipse at 20% 50%, rgba(108, 99, 255, 0.08) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 20%, rgba(224, 64, 251, 0.06) 0%, transparent 50%),
                radial-gradient(ellipse at 50% 80%, rgba(0, 210, 255, 0.05) 0%, transparent 50%);
            z-index: 0;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 24px;
            position: relative;
            z-index: 1;
        }

        /* Header */
        header {
            padding: 24px 0;
            border-bottom: 1px solid var(--border);
            backdrop-filter: blur(20px);
            background: rgba(10, 10, 15, 0.8);
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .header-inner {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .logo {
            font-size: 1.8rem;
            font-weight: 800;
            background: var(--gradient-1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            letter-spacing: -0.5px;
        }

        .logo span {
            font-weight: 400;
            opacity: 0.7;
        }

        nav {
            display: flex;
            gap: 8px;
        }

        .nav-btn {
            padding: 8px 20px;
            border-radius: 10px;
            border: 1px solid var(--border);
            background: transparent;
            color: var(--text-secondary);
            font-size: 0.9rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            font-family: inherit;
        }

        .nav-btn:hover, .nav-btn.active {
            background: var(--accent);
            color: white;
            border-color: var(--accent);
            box-shadow: 0 4px 15px var(--accent-glow);
        }

        /* Hero */
        .hero {
            text-align: center;
            padding: 80px 0 60px;
        }

        .hero-badge {
            display: inline-block;
            padding: 6px 16px;
            border-radius: 50px;
            background: rgba(108, 99, 255, 0.15);
            border: 1px solid rgba(108, 99, 255, 0.3);
            color: var(--accent-light);
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 24px;
        }

        .hero h1 {
            font-size: 3.5rem;
            font-weight: 900;
            line-height: 1.1;
            margin-bottom: 20px;
            letter-spacing: -1.5px;
        }

        .hero h1 .gradient-text {
            background: var(--gradient-1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .hero p {
            font-size: 1.2rem;
            color: var(--text-secondary);
            max-width: 600px;
            margin: 0 auto 40px;
            line-height: 1.6;
        }

        /* Stats */
        .stats-row {
            display: flex;
            justify-content: center;
            gap: 40px;
            margin-bottom: 60px;
        }

        .stat-item {
            text-align: center;
        }

        .stat-number {
            font-size: 2.5rem;
            font-weight: 800;
            background: var(--gradient-2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .stat-label {
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-top: 4px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        /* Tabs */
        .section-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 32px;
        }

        .section-title {
            font-size: 1.5rem;
            font-weight: 700;
        }

        .filter-row {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 24px;
        }

        .filter-chip {
            padding: 6px 14px;
            border-radius: 8px;
            border: 1px solid var(--border);
            background: var(--bg-secondary);
            color: var(--text-secondary);
            font-size: 0.8rem;
            cursor: pointer;
            transition: all 0.2s;
            font-family: inherit;
        }

        .filter-chip:hover, .filter-chip.active {
            background: var(--accent);
            color: white;
            border-color: var(--accent);
        }

        /* Cards */
        .cards-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }

        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            transition: all 0.3s;
            cursor: pointer;
            text-decoration: none;
            color: inherit;
            display: block;
        }

        .card:hover {
            background: var(--bg-card-hover);
            border-color: var(--accent);
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3), 0 0 20px var(--accent-glow);
        }

        .card-source {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 6px;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 12px;
        }

        .source-techcrunch { background: rgba(0, 200, 83, 0.15); color: #4ade80; }
        .source-venturebeat { background: rgba(255, 107, 107, 0.15); color: #ff6b6b; }
        .source-therundown { background: rgba(108, 99, 255, 0.15); color: #8b83ff; }
        .source-openai { background: rgba(0, 210, 255, 0.15); color: #00d2ff; }
        .source-ai-news { background: rgba(251, 191, 36, 0.15); color: #fbbf24; }
        .source-futuretools { background: rgba(224, 64, 251, 0.15); color: #e040fb; }
        .source-futurepedia { background: rgba(0, 210, 255, 0.15); color: #00d2ff; }
        .source-default { background: rgba(160, 160, 181, 0.15); color: var(--text-secondary); }

        .card-title {
            font-size: 1.05rem;
            font-weight: 600;
            line-height: 1.4;
            margin-bottom: 8px;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }

        .card-summary {
            font-size: 0.85rem;
            color: var(--text-secondary);
            line-height: 1.6;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
            margin-bottom: 16px;
        }

        .card-meta {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.75rem;
            color: var(--text-muted);
        }

        .card-pricing {
            padding: 3px 10px;
            border-radius: 6px;
            font-size: 0.7rem;
            font-weight: 600;
        }

        .pricing-free { background: rgba(74, 222, 128, 0.15); color: #4ade80; }
        .pricing-freemium { background: rgba(251, 191, 36, 0.15); color: #fbbf24; }
        .pricing-paid { background: rgba(255, 107, 107, 0.15); color: #ff6b6b; }

        /* Ladeanimation */
        .loading {
            text-align: center;
            padding: 60px;
            color: var(--text-muted);
        }

        .spinner {
            width: 40px;
            height: 40px;
            border: 3px solid var(--border);
            border-top-color: var(--accent);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin: 0 auto 16px;
        }

        @keyframes spin { to { transform: rotate(360deg); } }

        /* Load More */
        .load-more {
            display: block;
            margin: 0 auto 60px;
            padding: 12px 40px;
            border-radius: 12px;
            border: 1px solid var(--border);
            background: var(--bg-secondary);
            color: var(--text-secondary);
            font-size: 0.9rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            font-family: inherit;
        }

        .load-more:hover {
            background: var(--accent);
            color: white;
            border-color: var(--accent);
        }

        /* Footer */
        footer {
            border-top: 1px solid var(--border);
            padding: 40px 0;
            text-align: center;
            color: var(--text-muted);
            font-size: 0.85rem;
        }

        .footer-links {
            display: flex;
            justify-content: center;
            gap: 24px;
            margin-bottom: 16px;
        }

        .footer-links a {
            color: var(--text-secondary);
            text-decoration: none;
            transition: color 0.2s;
        }

        .footer-links a:hover { color: var(--accent); }

        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: var(--text-muted);
        }

        .empty-state svg {
            width: 64px;
            height: 64px;
            margin-bottom: 16px;
            opacity: 0.3;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .hero h1 { font-size: 2.2rem; }
            .hero p { font-size: 1rem; }
            .stats-row { gap: 24px; flex-wrap: wrap; }
            .stat-number { font-size: 1.8rem; }
            .cards-grid { grid-template-columns: 1fr; }
            .header-inner { flex-direction: column; gap: 16px; }
            nav { width: 100%; justify-content: center; }
        }
    </style>
</head>
<body>
    <div class="bg-gradient"></div>

    <header>
        <div class="container header-inner">
            <div class="logo">app<span>.ki</span></div>
            <nav>
                <button class="nav-btn active" onclick="showSection('news')">News</button>
                <button class="nav-btn" onclick="showSection('tools')">Tools</button>
                <a href="/docs" class="nav-btn" style="text-decoration:none;">API Docs</a>
            </nav>
        </div>
    </header>

    <main>
        <section class="hero">
            <div class="container">
                <div class="hero-badge">Automatisch aktualisiert</div>
                <h1>Die neuesten<br><span class="gradient-text">KI-News & Tools</span></h1>
                <p>Täglich automatisch gesammelt aus den besten amerikanischen Quellen. Immer aktuell, immer relevant.</p>
                <div class="stats-row">
                    <div class="stat-item">
                        <div class="stat-number" id="stat-news">—</div>
                        <div class="stat-label">News-Artikel</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="stat-tools">—</div>
                        <div class="stat-label">KI-Tools</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number">5+</div>
                        <div class="stat-label">Quellen</div>
                    </div>
                </div>
            </div>
        </section>

        <!-- News Section -->
        <section id="section-news" class="container">
            <div class="section-header">
                <h2 class="section-title">Aktuelle KI-News</h2>
            </div>
            <div class="filter-row" id="news-filters"></div>
            <div class="cards-grid" id="news-cards">
                <div class="loading"><div class="spinner"></div>Lade News...</div>
            </div>
            <button class="load-more" id="news-load-more" onclick="loadMoreNews()" style="display:none;">Mehr laden</button>
        </section>

        <!-- Tools Section -->
        <section id="section-tools" class="container" style="display:none;">
            <div class="section-header">
                <h2 class="section-title">KI-Tools Verzeichnis</h2>
            </div>
            <div class="filter-row" id="tools-filters"></div>
            <div class="cards-grid" id="tools-cards">
                <div class="loading"><div class="spinner"></div>Lade Tools...</div>
            </div>
            <button class="load-more" id="tools-load-more" onclick="loadMoreTools()" style="display:none;">Mehr laden</button>
        </section>
    </main>

    <footer>
        <div class="container">
            <div class="footer-links">
                <a href="/docs">API-Dokumentation</a>
                <a href="/api/stats">Statistiken</a>
            </div>
            <p>&copy; 2025 app.ki — Automatisch aggregierte KI-Informationen</p>
        </div>
    </footer>

    <script>
        const API_BASE = '';
        let newsOffset = 0;
        let toolsOffset = 0;
        let activeNewsSource = null;
        let activeToolsCategory = null;

        // Hilfsfunktionen
        function getSourceClass(source) {
            const map = {
                'techcrunch': 'source-techcrunch',
                'venturebeat': 'source-venturebeat',
                'therundown': 'source-therundown',
                'openai': 'source-openai',
                'ai-news': 'source-ai-news',
                'futuretools': 'source-futuretools',
                'futurepedia': 'source-futurepedia',
            };
            return map[source] || 'source-default';
        }

        function formatDate(dateStr) {
            if (!dateStr) return '';
            const d = new Date(dateStr);
            const now = new Date();
            const diff = Math.floor((now - d) / (1000 * 60 * 60));
            if (diff < 1) return 'Gerade eben';
            if (diff < 24) return `vor ${diff}h`;
            if (diff < 48) return 'Gestern';
            return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' });
        }

        function stripHtml(html) {
            const tmp = document.createElement('div');
            tmp.innerHTML = html;
            return tmp.textContent || tmp.innerText || '';
        }

        // Abschnitte umschalten
        function showSection(section) {
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('section-news').style.display = section === 'news' ? 'block' : 'none';
            document.getElementById('section-tools').style.display = section === 'tools' ? 'block' : 'none';

            if (section === 'tools' && document.getElementById('tools-cards').children.length <= 1) {
                loadTools();
                loadToolsFilters();
            }
        }

        // News laden
        async function loadNews(append = false) {
            if (!append) {
                newsOffset = 0;
                document.getElementById('news-cards').innerHTML = '<div class="loading"><div class="spinner"></div>Lade News...</div>';
            }

            let url = `${API_BASE}/api/news?limit=20&offset=${newsOffset}`;
            if (activeNewsSource) url += `&source=${activeNewsSource}`;

            try {
                const res = await fetch(url);
                const data = await res.json();

                if (!append) document.getElementById('news-cards').innerHTML = '';

                if (data.length === 0 && !append) {
                    document.getElementById('news-cards').innerHTML = '<div class="empty-state"><p>Noch keine News vorhanden. Die Scraper laufen täglich automatisch.</p></div>';
                    document.getElementById('news-load-more').style.display = 'none';
                    return;
                }

                data.forEach(item => {
                    const summary = item.summary ? stripHtml(item.summary) : '';
                    const card = document.createElement('a');
                    card.className = 'card';
                    card.href = item.url;
                    card.target = '_blank';
                    card.rel = 'noopener';
                    card.innerHTML = `
                        <span class="card-source ${getSourceClass(item.source)}">${item.source || 'Unbekannt'}</span>
                        <h3 class="card-title">${item.title}</h3>
                        ${summary ? `<p class="card-summary">${summary}</p>` : ''}
                        <div class="card-meta">
                            <span>${formatDate(item.published_at || item.fetched_at)}</span>
                            <span>${item.category || ''}</span>
                        </div>
                    `;
                    document.getElementById('news-cards').appendChild(card);
                });

                newsOffset += data.length;
                document.getElementById('news-load-more').style.display = data.length >= 20 ? 'block' : 'none';
            } catch (e) {
                console.error('Fehler beim Laden der News:', e);
                if (!append) {
                    document.getElementById('news-cards').innerHTML = '<div class="empty-state"><p>Fehler beim Laden der News.</p></div>';
                }
            }
        }

        function loadMoreNews() { loadNews(true); }

        // Tools laden
        async function loadTools(append = false) {
            if (!append) {
                toolsOffset = 0;
                document.getElementById('tools-cards').innerHTML = '<div class="loading"><div class="spinner"></div>Lade Tools...</div>';
            }

            let url = `${API_BASE}/api/tools?limit=20&offset=${toolsOffset}`;
            if (activeToolsCategory) url += `&category=${activeToolsCategory}`;

            try {
                const res = await fetch(url);
                const data = await res.json();

                if (!append) document.getElementById('tools-cards').innerHTML = '';

                if (data.length === 0 && !append) {
                    document.getElementById('tools-cards').innerHTML = '<div class="empty-state"><p>Noch keine Tools vorhanden. Die Scraper laufen täglich automatisch.</p></div>';
                    document.getElementById('tools-load-more').style.display = 'none';
                    return;
                }

                data.forEach(item => {
                    const card = document.createElement('a');
                    card.className = 'card';
                    card.href = item.url || '#';
                    card.target = '_blank';
                    card.rel = 'noopener';
                    card.innerHTML = `
                        <span class="card-source ${getSourceClass(item.source)}">${item.source || 'Unbekannt'}</span>
                        <h3 class="card-title">${item.name}</h3>
                        ${item.description ? `<p class="card-summary">${item.description}</p>` : ''}
                        <div class="card-meta">
                            <span>${item.category || ''}</span>
                            ${item.pricing ? `<span class="card-pricing pricing-${item.pricing}">${item.pricing}</span>` : ''}
                        </div>
                    `;
                    document.getElementById('tools-cards').appendChild(card);
                });

                toolsOffset += data.length;
                document.getElementById('tools-load-more').style.display = data.length >= 20 ? 'block' : 'none';
            } catch (e) {
                console.error('Fehler beim Laden der Tools:', e);
                if (!append) {
                    document.getElementById('tools-cards').innerHTML = '<div class="empty-state"><p>Fehler beim Laden der Tools.</p></div>';
                }
            }
        }

        function loadMoreTools() { loadTools(true); }

        // Filter laden
        async function loadNewsFilters() {
            try {
                const res = await fetch(`${API_BASE}/api/news/sources`);
                const sources = await res.json();
                const container = document.getElementById('news-filters');
                container.innerHTML = '<button class="filter-chip active" onclick="filterNews(null, this)">Alle</button>';
                sources.forEach(s => {
                    container.innerHTML += `<button class="filter-chip" onclick="filterNews('${s}', this)">${s}</button>`;
                });
            } catch (e) { console.error('Fehler beim Laden der Filter:', e); }
        }

        async function loadToolsFilters() {
            try {
                const res = await fetch(`${API_BASE}/api/tools/categories`);
                const cats = await res.json();
                const container = document.getElementById('tools-filters');
                container.innerHTML = '<button class="filter-chip active" onclick="filterTools(null, this)">Alle</button>';
                cats.forEach(c => {
                    container.innerHTML += `<button class="filter-chip" onclick="filterTools('${c}', this)">${c}</button>`;
                });
            } catch (e) { console.error('Fehler beim Laden der Filter:', e); }
        }

        function filterNews(source, btn) {
            activeNewsSource = source;
            document.querySelectorAll('#news-filters .filter-chip').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            loadNews();
        }

        function filterTools(cat, btn) {
            activeToolsCategory = cat;
            document.querySelectorAll('#tools-filters .filter-chip').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            loadTools();
        }

        // Statistiken laden
        async function loadStats() {
            try {
                const res = await fetch(`${API_BASE}/api/stats`);
                const data = await res.json();
                document.getElementById('stat-news').textContent = data.news_gesamt.toLocaleString('de-DE');
                document.getElementById('stat-tools').textContent = data.tools_gesamt.toLocaleString('de-DE');
            } catch (e) {
                console.error('Fehler beim Laden der Statistiken:', e);
            }
        }

        // Initialisierung
        document.addEventListener('DOMContentLoaded', () => {
            loadStats();
            loadNews();
            loadNewsFilters();
        });
    </script>
</body>
</html>"""


# --- API Endpoints ---

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root(username: str = Depends(verify_credentials)):
    """Startseite — moderne Weboberflaeche fuer app.ki (passwortgeschuetzt)"""
    return HTMLResponse(content=FRONTEND_HTML)


@app.get("/api/status", response_model=StatusResponse, tags=["System"])
async def get_status():
    """Status und Version der API."""
    return StatusResponse(status="online", version="1.0.0", project="app.ki")


@app.get("/api/stats", response_model=StatsResponse, tags=["System"])
async def get_stats(db: Session = Depends(get_db)):
    """Gibt die Gesamtanzahl der News und Tools zurück."""
    news_count = db.query(AiNews).count()
    tools_count = db.query(AiTools).count()
    return StatsResponse(news_gesamt=news_count, tools_gesamt=tools_count)


@app.post("/api/admin/fetch-now", tags=["Admin"])
async def fetch_now():
    """Startet alle Scraper sofort (fuer Tests und manuelle Aktualisierung).
    Fuehrt die 2-Stufen-Pipeline aus:
      1. Collector — sammelt Tool-Namen und URLs
      2. Enrichment Agent — holt Details fuer pending Tools
    """
    logger.info("Manueller Scraper-Start ausgeloest via /api/admin/fetch-now")
    db = SessionLocal()
    try:
        rss_count = fetch_all_rss_feeds(db)
        collected_count = collect_all_tools(db)
        enrichment_result = enrich_pending_tools(db)
        return {
            "status": "completed",
            "neue_news": rss_count,
            "neue_tools_gesammelt": collected_count,
            "enrichment": enrichment_result,
        }
    except Exception as e:
        logger.error(f"Fehler beim manuellen Fetch: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": str(e)},
        )
    finally:
        db.close()

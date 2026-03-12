#!/bin/bash
# install.sh — Einzeiler-Installation für app.ki
# Voraussetzung: Ubuntu 24.04 / Debian 12 Server
set -e

echo "=== app.ki Installation startet ==="

# Prüfe ob .env vorhanden ist
if [ ! -f /opt/appki/.env ]; then
    echo "FEHLER: /opt/appki/.env nicht gefunden!"
    echo "Bitte zuerst .env.example kopieren und anpassen:"
    echo "  cp /opt/appki/.env.example /opt/appki/.env"
    exit 1
fi

# Lade Umgebungsvariablen
source /opt/appki/.env

# 1. System-Pakete installieren
echo "=== Installiere System-Pakete ==="
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3 python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib libpq-dev gcc nginx curl git \
    certbot python3-certbot-nginx

# 2. PostgreSQL einrichten
echo "=== Konfiguriere PostgreSQL ==="
systemctl start postgresql
systemctl enable postgresql
sudo -u postgres psql -c "CREATE USER ${POSTGRES_USER} WITH PASSWORD '${POSTGRES_PASSWORD}';" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE ${POSTGRES_DB} OWNER ${POSTGRES_USER};" 2>/dev/null || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${POSTGRES_DB} TO ${POSTGRES_USER};" 2>/dev/null || true

# 3. Python Virtual Environment
echo "=== Erstelle Python Virtual Environment ==="
python3 -m venv /opt/appki/venv
source /opt/appki/venv/bin/activate
pip install --upgrade pip
pip install -r /opt/appki/requirements.txt

# 4. Nginx konfigurieren
echo "=== Konfiguriere Nginx ==="
cp /opt/appki/nginx.conf /etc/nginx/sites-available/appki
ln -sf /etc/nginx/sites-available/appki /etc/nginx/sites-enabled/appki
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx
systemctl enable nginx

# 5. systemd Service einrichten
echo "=== Konfiguriere systemd Service ==="
cp /opt/appki/appki.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable appki
systemctl start appki

# 6. Funktionstest
echo "=== Teste Installation ==="
sleep 3
if curl -sf http://localhost/ > /dev/null; then
    echo "app.ki laeuft erfolgreich!"
else
    echo "WARNUNG: app.ki antwortet noch nicht. Pruefe Logs mit: journalctl -u appki -f"
fi

echo "=== Installation abgeschlossen ==="

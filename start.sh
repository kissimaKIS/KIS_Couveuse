#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "============================================"
echo "  GESTION COUVEUSE - Démarrage de l'application"
echo "============================================"

# --- 1. Vérifier / démarrer PostgreSQL local --------------------------------
echo "[1/4] Vérification de PostgreSQL..."
if command -v pg_isready >/dev/null 2>&1 && pg_isready -q; then
    echo "  PostgreSQL est déjà démarré."
else
    if command -v systemctl >/dev/null 2>&1; then
        sudo systemctl start postgresql || true
    elif command -v brew >/dev/null 2>&1; then
        brew services start postgresql || true
    elif command -v pg_ctlcluster >/dev/null 2>&1; then
        sudo pg_ctlcluster $(pg_lsclusters -h | awk '{print $1}' | head -n1) main start || true
    else
        echo "  Impossible de démarrer PostgreSQL automatiquement sur ce système."
        echo "  Démarrez-le manuellement puis relancez ce script."
    fi
fi

# --- 2. Activer l'environnement virtuel -------------------------------------
echo "[2/4] Activation de l'environnement virtuel..."
if [ ! -d "venv" ]; then
    echo "  Aucun environnement virtuel trouvé, création en cours..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# --- 3. Migrations -----------------------------------------------------------
echo "[3/4] Vérification de la base de données..."
python manage.py migrate --noinput

# --- 4. Lancer le serveur et ouvrir le navigateur ----------------------------
echo "[4/4] Démarrage du serveur Django..."
python manage.py runserver 127.0.0.1:8000 &
SERVER_PID=$!

sleep 3

URL="http://127.0.0.1:8000"
if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL"
elif command -v open >/dev/null 2>&1; then
    open "$URL"
else
    echo "Ouvrez manuellement votre navigateur à l'adresse $URL"
fi

echo "L'application tourne (PID $SERVER_PID). Appuyez sur Ctrl+C pour l'arrêter."
wait $SERVER_PID

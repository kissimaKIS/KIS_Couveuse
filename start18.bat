@echo off
setlocal enabledelayedexpansion
title Gestion Couveuse - Demarrage
cd /d "%~dp0"

echo ============================================
echo   GESTION COUVEUSE - Demarrage de l'application
echo ============================================

REM --- 1. Verifier / demarrer le service PostgreSQL local -------------------
echo [1/4] verification du service postgresql...
sc query postgresql-x64-18 >nul 2>&1
if %errorlevel%==0 (
    set pg_service=postgresql-x64-18
) else (
    for /f "tokens=3" %%s in ('sc query state^= all ^| findstr /i "postgresql"') do set pg_service=%%s
)

sc query "%pg_service%" | findstr "running" >nul
if errorlevel 1 (
    echo demarrage du service postgresql "%pg_service%"...
    net start "%pg_service%" >nul 2>&1
) else (
    echo postgresql est deja demarre.
)

REM --- 2. Activer l'environnement virtuel ------------------------------------
echo [2/4] Activation de l'environnement virtuel...
if not exist "venv\Scripts\activate.bat" (
    echo   Aucun environnement virtuel trouve, creation en cours...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

REM --- 3. Appliquer les migrations et lancer le serveur Django ---------------
echo [3/4] Verification de la base de donnees...
python manage.py migrate --noinput

echo [4/4] Demarrage du serveur Django...
start "Serveur Django - Couveuse" cmd /k "call venv\Scripts\activate.bat && python manage.py runserver 127.0.0.1:8000"

REM --- 4. Ouvrir le navigateur par defaut ------------------------------------
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:8000"

echo.
echo L'application est lancee. Vous pouvez fermer cette fenetre.
pause >nul

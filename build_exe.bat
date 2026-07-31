@echo off
setlocal
title Gestion Couveuse - Compilation .exe
cd /d "%~dp0"

echo ============================================
echo   COMPILATION DE GestionCouveuse.exe
echo ============================================

REM --- 1. Activer l'environnement virtuel ------------------------------------
if not exist "venv\Scripts\activate.bat" (
    echo Environnement virtuel introuvable. Lancez d'abord start.bat une fois,
    echo ou creez-le manuellement : python -m venv venv
    pause
    exit /b 1
)
call venv\Scripts\activate.bat

REM --- 2. Verifier que PyInstaller est installe -------------------------------
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installation de PyInstaller...
    pip install pyinstaller
)

REM --- 3. Verifier la presence de l'icone et du fichier de version -----------
if not exist "icon.ico" (
    echo [ATTENTION] icon.ico introuvable a la racine du projet.
    echo Placez votre propre icone ^(format .ico^) sous ce nom, ou utilisez
    echo celle fournie par defaut.
    pause
    exit /b 1
)
if not exist "version_info.txt" (
    echo [ATTENTION] version_info.txt introuvable a la racine du projet.
    pause
    exit /b 1
)

REM --- 4. Nettoyer les anciens builds -----------------------------------------
echo Nettoyage des builds precedents...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

REM --- 5. Compiler avec le fichier .spec (icone + version_info deja references)
echo Compilation en cours (cela peut prendre plusieurs minutes)...
python -m PyInstaller GestionCouveuse.spec

if errorlevel 1 (
    echo.
    echo La compilation a echoue. Consultez les messages ci-dessus.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   TERMINE : dist\GestionCouveuse.exe
echo ============================================
echo Vous pouvez distribuer ce fichier .exe seul ^(mode --onefile^).
echo N'oubliez pas : PostgreSQL doit etre installe sur la machine cible,
echo et le fichier .env doit se trouver a cote de l'executable.
pause

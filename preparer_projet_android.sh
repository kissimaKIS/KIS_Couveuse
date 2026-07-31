#!/usr/bin/env bash
# Copie le code Django (core/, couveuse_project/) et les fichiers
# templates/static dans le projet Android Studio, aux emplacements attendus
# par Chaquopy et par AssetExtractor.kt.
#
# IMPORTANT : générez d'abord les migrations sur le projet desktop avant de
# lancer ce script, sinon la version mobile n'aura pas de schéma de base :
#   python manage.py makemigrations core
#
# Usage : ./preparer_projet_android.sh
set -e
cd "$(dirname "$0")/.."   # racine du projet Django (contient manage.py)

DEST_PYTHON="android_project/app/src/main/python"
DEST_ASSETS="android_project/app/src/main/assets/django_app"

echo "Copie de core/ et couveuse_project/ vers $DEST_PYTHON ..."
rm -rf "$DEST_PYTHON/core" "$DEST_PYTHON/couveuse_project"
cp -r core "$DEST_PYTHON/core"
cp -r couveuse_project "$DEST_PYTHON/couveuse_project"

# Nettoyage : pas besoin des fichiers de dev sur mobile.
find "$DEST_PYTHON/core" "$DEST_PYTHON/couveuse_project" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

echo "Copie de templates/ et static/ vers $DEST_ASSETS ..."
rm -rf "$DEST_ASSETS/templates" "$DEST_ASSETS/static"
mkdir -p "$DEST_ASSETS"
cp -r templates "$DEST_ASSETS/templates"
cp -r static "$DEST_ASSETS/static"

echo "Terminé. Ouvrez android_project/ dans Android Studio, laissez Gradle"
echo "synchroniser, puis lancez l'app sur un émulateur ou un téléphone connecté."

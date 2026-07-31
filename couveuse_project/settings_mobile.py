"""
Variante des réglages pour la version Android (Chaquopy).
Utilisée via DJANGO_SETTINGS_MODULE=couveuse_project.settings_mobile
Voir android_project/ pour le projet Android Studio complet, et
android/README.md pour l'explication de l'architecture.

COUVEUSE_MOBILE_BASE_DIR est fourni par mobile_entrypoint.py : c'est le
dossier réel du stockage interne de l'app (pas l'APK) où AssetExtractor.kt
a copié templates/ et static/, et où Django lit/écrit sa base SQLite.
"""
import os
from pathlib import Path

from .settings import *  # noqa

DEBUG = False

_BASE_MOBILE = Path(os.environ.get("COUVEUSE_MOBILE_BASE_DIR", BASE_DIR))

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(_BASE_MOBILE / "couveuse_mobile.sqlite3"),
    }
}

TEMPLATES[0]["DIRS"] = [_BASE_MOBILE / "templates"]

STATIC_URL = "static/"
STATICFILES_DIRS = [_BASE_MOBILE / "static"]
STATIC_ROOT = _BASE_MOBILE / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = _BASE_MOBILE / "media"

# Sur mobile, l'app se comporte comme une station déjà activée et déjà
# configurée après le premier lancement sur PC : rien n'empêche de
# pré-remplir la licence et le compte admin lors du build (fixtures) pour un
# démarrage direct sur le téléphone, sans repasser par les deux écrans de
# setup — à faire via une fixture chargée dans mobile_entrypoint.demarrer().

"""
Point d'entrée pour Android.
"""
import os
import shutil
from datetime import datetime


def _preparer_django(chemin_base, device_id=None):
    os.environ["COUVEUSE_MOBILE_BASE_DIR"] = chemin_base
    if device_id:
        os.environ["COUVEUSE_DEVICE_ID"] = device_id
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "couveuse_project.settings_mobile")
    import django
    django.setup()


def demarrer(chemin_base, device_id):
    try:
        _demarrer_impl(chemin_base, device_id)
    except BaseException as e:
        print(f"CRASH FATAL Python (BaseException) : {type(e).__name__}: {e}")

def _demarrer_impl(chemin_base, device_id):
    _preparer_django(chemin_base, device_id)

    # Création des dossiers nécessaires
    from django.conf import settings
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
    os.makedirs(settings.STATIC_ROOT, exist_ok=True)
    os.makedirs(os.path.join(chemin_base, "sauvegardes"), exist_ok=True)

    from django.core.management import call_command

    # On ne lance migrate que si nécessaire (basé sur un flag de version dans les fichiers)
    # Pour simplifier on garde migrate car Django gère l'idempotence, mais on optimise seed_especes
    call_command("migrate", interactive=False, verbosity=0)

    # Création de l'utilisateur kis par défaut pour l'AutoLogin
    from django.contrib.auth import get_user_model
    User = get_user_model()
    if not User.objects.filter(username="kis").exists():
        User.objects.create_superuser("kis", "kis@kissima.com", "kis_password_2026")

    # OPTIMISATION : Ne lancer seed_especes que si la table est vide ou via flag v42
    from core.models import Espece
    if not Espece.objects.exists():
        try:
            print("Initialisation des espèces...")
            call_command("seed_especes")
        except Exception as e:
            print(f"ERREUR lors de seed_especes : {e}")

    try:
        print("Lancement du serveur Django sur 127.0.0.1:8080...")
        call_command("runserver", "127.0.0.1:8080", use_reloader=False)
    except BaseException as e:
        print(f"ERREUR : Le serveur Django n'a pas pu démarrer : {type(e).__name__}: {e}")


def compter_alertes(chemin_base, device_id=None):
    _preparer_django(chemin_base, device_id)

    # En profiter pour faire une sauvegarde journalière
    sauvegarder_db(chemin_base)

    from core.models import Depot
    depots_actifs = Depot.objects.filter(nombre_eclos__isnull=True).select_related("client", "espece")
    nb_mirage = sum(1 for d in depots_actifs if d.alerte_mirage_du_jour)
    nb_eclosion = sum(1 for d in depots_actifs if d.alerte_eclosion_proche)
    return {"mirage": nb_mirage, "eclosion": nb_eclosion}


def sauvegarder_db(chemin_base):
    """Copie la base SQLite dans un dossier de backup."""
    source = os.path.join(chemin_base, "couveuse_mobile.sqlite3")
    if not os.path.exists(source):
        return

    backup_dir = os.path.join(chemin_base, "sauvegardes")
    os.makedirs(backup_dir, exist_ok=True)

    # On garde une seule sauvegarde par jour
    nom_backup = f"backup_{datetime.now().strftime('%Y-%m-%d')}.sqlite3"
    destination = os.path.join(backup_dir, nom_backup)

    if not os.path.exists(destination) or True: # Force l'écrasement pour avoir le dernier état du jour
        shutil.copy2(source, destination)
        # Nettoyage : garder les 7 derniers jours seulement
        files = sorted([f for f in os.listdir(backup_dir) if f.startswith("backup_")])
        while len(files) > 7:
            os.remove(os.path.join(backup_dir, files.pop(0)))

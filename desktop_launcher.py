"""
Point d'entrée pour le packaging PyInstaller (exécutable Windows "double-clic").

Ce script :
1. Démarre le serveur Django (runserver) dans un thread en arrière-plan.
2. Affiche une icône dans la barre système (pystray) avec un menu
   "Ouvrir" / "Quitter", pour indiquer clairement que l'application tourne.
3. Ouvre automatiquement le navigateur par défaut sur l'application.

Build :
    build_exe.bat
    (utilise GestionCouveuse.spec, qui référence icon.ico et version_info.txt
    et inclut automatiquement templates/, static/ et les imports dynamiques
    de Django — voir GestionCouveuse.spec pour le détail)
"""
import os
import sys
import threading
import webbrowser
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "couveuse_project.settings")

HOTE = "127.0.0.1"
PORT = "8000"
URL = f"http://{HOTE}:{PORT}"


def demarrer_serveur():
    import django
    django.setup()
    from django.core.management import call_command
    call_command("migrate", interactive=False)

    # Pas de terminal disponible chez le client final pour lancer
    # "manage.py seed_especes" à la main : on l'exécute automatiquement au
    # premier démarrage, une seule fois (si la table Espece est vide).
    from core.models import Espece
    if not Espece.objects.exists():
        call_command("seed_especes")

    from django.core.management.commands.runserver import Command as RunServerCommand
    # use_reloader=False : indispensable en exécutable packagé (un seul process).
    call_command("runserver", f"{HOTE}:{PORT}", use_reloader=False)


def ouvrir_navigateur():
    time.sleep(2)
    webbrowser.open(URL)


def construire_icone():
    from PIL import Image, ImageDraw
    image = Image.new("RGB", (64, 64), color=(47, 111, 79))
    dessin = ImageDraw.Draw(image)
    dessin.ellipse((14, 10, 50, 54), fill=(255, 255, 255))
    return image


def lancer_barre_systeme():
    import pystray
    from pystray import MenuItem as Item

    def ouvrir(icon, item):
        webbrowser.open(URL)

    def quitter(icon, item):
        icon.stop()
        os._exit(0)

    menu = pystray.Menu(
        Item("Ouvrir l'application", ouvrir, default=True),
        Item("Quitter", quitter),
    )
    icon = pystray.Icon("GestionCouveuse", construire_icone(), "Gestion Couveuse", menu)
    icon.run()


if __name__ == "__main__":
    threading.Thread(target=demarrer_serveur, daemon=True).start()
    threading.Thread(target=ouvrir_navigateur, daemon=True).start()
    lancer_barre_systeme()

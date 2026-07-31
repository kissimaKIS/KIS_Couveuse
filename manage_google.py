#!/usr/bin/env python
import os
import sys
import subprocess
import time
from pathlib import Path

def gerer_postgres_embarque():
    # Détecter si l'application est compilée avec PyInstaller
    if not getattr(sys, 'frozen', False):
        return # En mode dev (python manage.py runserver), on ne fait rien

    base_dir = Path(sys._MEIPASS) if hasattr(sys, '_MEIPASS') else Path(sys.executable).parent
    
    # Si le dossier 'pgsql' est présent dans le dossier du EXE, on est en mode DISTRIBUÉ (Onedir)
    pg_bin_dir = base_dir / "pgsql" / "bin"
    if not pg_bin_dir.exists():
        return # Mode personnel (Onefile) : l'utilisateur utilise son Postgres local, on ne fait rien

    pg_data_dir = Path(sys.executable).parent / "db_data"

    # 1. Initialisation de la BDD si premier lancement
    if not pg_data_dir.exists():
        initdb_exe = pg_bin_dir / "initdb.exe"
        # Initialisation sécurisée sans mot de passe requis en local (trust)
        subprocess.run([str(initdb_exe), "-D", str(pg_data_dir), "-U", "postgres", "--auth=trust"], check=True)

    # 2. Démarrage de Postgres au niveau utilisateur (SANS DROITS ADMIN)
    pg_ctl_exe = pg_bin_dir / "pg_ctl.exe"
    try:
        subprocess.Popen(
            [str(pg_ctl_exe), "start", "-D", str(pg_data_dir), "-o", "-F -p 5432"],
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        time.sleep(2) # On laisse 2 secondes à Postgres pour respirer et démarrer
    except Exception as e:
        print(f"Erreur Postgres Embarqué: {e}")

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'couveuse_project.settings')
    
    # Lancement automatique de Postgres si applicable
    gerer_postgres_embarque()
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()

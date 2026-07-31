import os
import json
import hashlib
from datetime import datetime
from pathlib import Path

# =========================
# CONFIG
# =========================

SECRET = "KIS_SECRET_2026"

def get_data_dir():
    # Sur Android, COUVEUSE_MOBILE_BASE_DIR est le dossier de stockage interne
    return Path(os.environ.get("COUVEUSE_MOBILE_BASE_DIR", "."))

def get_license_file():
    path = get_data_dir() / "licence.dat"
    print(f"DEBUG Path - Fichier licence : {path}")
    return path

def get_clock_file():
    path = get_data_dir() / "sys_cache.bin"
    print(f"DEBUG Path - Fichier horloge : {path}")
    return path

# =========================
# MACHINE ID (Android)
# =========================

def get_machine_id():
    """Récupère l'ID Android passé par Kotlin via mobile_entrypoint."""
    # On force les majuscules partout pour éviter les erreurs de signature
    return os.environ.get("COUVEUSE_DEVICE_ID", "ID_INCONNU").upper()

def get_display_id():
    """Identifiant complet à envoyer pour activation."""
    return get_machine_id().upper()

# =========================
# SIGNATURE
# =========================

def generate_signature(machine, days, expiry_str):
    raw = machine + SECRET + str(days) + expiry_str
    sig = hashlib.sha256(raw.encode()).hexdigest()
    return sig[:8].upper()

def generate_license_fingerprint(key):
    raw = key + SECRET
    return hashlib.sha256(raw.encode()).hexdigest()

# =========================
# CHECK LICENCE
# =========================

def check_license():
    license_file = get_license_file()
    clock_file = get_clock_file()

    if not license_file.exists():
        return False

    try:
        data = json.loads(license_file.read_text())
        key = data.get("key")
        expiry_date = datetime.strptime(data.get("expiry"), "%Y-%m-%d")

        # 1. Vérification date expiration
        if datetime.now() > expiry_date:
            return False

        # 2. Décomposition de la clé KIS-XXXX-XXXX-DAYS-YYYYMMDD
        parts = key.split("-")
        if len(parts) != 5:
            return False

        sig_part = (parts[1] + parts[2]).upper()
        days = int(parts[3])
        expiry_str = parts[4]

        # 3. Vérification cohérence date
        if expiry_date.strftime("%Y%m%d") != expiry_str:
            return False

        # 4. Vérification signature machine
        machine = get_machine_id()
        expected_sig = generate_signature(machine, days, expiry_str)

        if sig_part != expected_sig:
            return False

        # 5. Protection horloge
        if clock_file.exists():
            try:
                cache = json.loads(clock_file.read_text())
                last_date_str = cache.get("last_date")
                if last_date_str:
                    last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
                    if datetime.now() < last_date:
                        # Retour en arrière de l'horloge détecté
                        return False

                # Vérification empreinte pour éviter la copie de sys_cache.bin
                saved_fp = cache.get("fingerprint")
                if saved_fp and saved_fp != generate_license_fingerprint(key):
                    return False
            except:
                pass

        # Mise à jour de l'horloge
        save_clock(key)

        return True

    except Exception:
        return False

def save_clock(key):
    try:
        data_dir = get_data_dir()
        os.makedirs(data_dir, exist_ok=True)
        clock_file = get_clock_file()
        data = {
            "last_date": datetime.now().strftime("%Y-%m-%d"),
            "fingerprint": generate_license_fingerprint(key)
        }
        clock_file.write_text(json.dumps(data))
    except:
        pass

# =========================
# GESTION LICENCE
# =========================

def save_license(key):
    """Valide et enregistre une clé dans le fichier licence.dat."""
    try:
        if not key or not isinstance(key, str):
            print("ERREUR: Clé vide ou type invalide")
            return False

        parts = key.split("-")
        if len(parts) != 5:
            print(f"ERREUR: Format de clé invalide (parts={len(parts)})")
            return False

        days = int(parts[3])
        expiry_str = parts[4]
        expiry_date = datetime.strptime(expiry_str, "%Y%m%d")

        machine = get_machine_id()
        sig_part = (parts[1] + parts[2]).upper()
        expected_sig = generate_signature(machine, days, expiry_str)

        if sig_part != expected_sig:
            print(f"ERREUR: Signature mismatch. Reçu: {sig_part}, Attendu: {expected_sig} (Machine: {machine})")
            return False

        data_dir = get_data_dir()
        os.makedirs(data_dir, exist_ok=True)

        data = {
            "key": key.upper(),
            "expiry": expiry_date.strftime("%Y-%m-%d")
        }
        get_license_file().write_text(json.dumps(data))
        save_clock(key)
        print("SUCCÈS: Licence sauvegardée avec succès.")
        return True
    except Exception as e:
        print(f"EXCEPTION dans save_license: {e}")
        return False

def get_remaining_days():
    """Calcule le nombre de jours restants avant expiration."""
    license_file = get_license_file()
    if not license_file.exists():
        return 0
    try:
        data = json.loads(license_file.read_text())
        expiry = datetime.strptime(data["expiry"], "%Y-%m-%d")
        delta = (expiry - datetime.now()).days
        return max(delta, 0)
    except:
        return 0

def get_license_info():
    """Retourne les détails pour l'affichage."""
    license_file = get_license_file()
    if not license_file.exists():
        return {"type": "Aucune", "expire": None, "jours": 0}

    try:
        data = json.loads(license_file.read_text())
        key = data.get("key", "")
        expiry_str = data.get("expiry")

        parts = key.split("-")
        days = int(parts[3]) if len(parts) == 5 else 0

        if days >= 90000:
            licence_type = "Permanente"
        else:
            licence_type = f"Abonnement ({days} jours)"

        return {
            "type": licence_type,
            "expire": expiry_str,
            "jours": get_remaining_days()
        }
    except:
        return {"type": "Invalide", "expire": None, "jours": 0}

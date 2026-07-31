"""
Générateur de clés PRO pour KIS Couveuse Apps.
A garder précieusement sur votre ordinateur.
"""
import hashlib

SECRET_SALT = "KIS-COUV-SALT-2026-X99"

def generer_cle(machine_id):
    # L'utilisateur envoie CUV-XXXX (8 chars), on nettoie
    clean_id = machine_id.replace("CUV-", "").strip().upper()

    # On recalcule le hash (doit correspondre à la logique AndroidID)
    # Note: AndroidID est plus long, mais l'app nous envoie le début
    # Pour que cela marche sans ID complet, l'app mobile doit fournir
    # l'ID complet via WhatsApp ou on doit changer la logique.
    # ICI, on va demander au client son identifiant complet affiché.

    payload = f"{SECRET_SALT}-{machine_id}"
    full_hash = hashlib.sha256(payload.encode()).hexdigest().upper()

    cle = f"PRO-{full_hash[:4]}-{full_hash[4:8]}-{full_hash[8:12]}"
    return cle

if __name__ == "__main__":
    print("--- GENERATEUR DE CLES KIS COUVEUSE ---")
    while True:
        mid = input("\nEntrez l'ID Appareil (ex: CUV-88AFB2) ou 'q' pour quitter : ")
        if mid.lower() == 'q': break

        try:
            cle = generer_cle(mid)
            print(f"CLE PRO A ENVOYER : {cle}")
        except Exception as e:
            print(f"Erreur : {e}")

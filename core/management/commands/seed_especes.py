"""
Initialisation des espèces avec icônes et paramètres par défaut.
"""
from django.core.management.base import BaseCommand
from core.models import Espece

DONNEES = [
    ("Poule", 150, 21, "icones_especes/Poule.webp"),
    ("Pintade", 150, 26, "icones_especes/Pintade.jpg"),
    ("Dinde", 300, 26, "icones_especes/Dinde.jpg"),
    ("Oie", 500, 30, "icones_especes/Oie.jpg"),
    ("Pigeon", 150, 16, "icones_especes/Pigeon.jpg"),
    ("Caille", 50, 18, "icones_especes/Caille.jpg"),
    ("CanneO", 300, 26, "icones_especes/CanneO.jpg"),
    ("CanneB", 300, 26, "icones_especes/CanneB.png"),
]

class Command(BaseCommand):
    help = "Initialise les espèces avec prix, durée et icônes."

    def handle(self, *args, **options):
        for nom, prix, duree, icone in DONNEES:
            espece, cree = Espece.objects.get_or_create(
                nom=nom,
                defaults={
                    "prix_unitaire": prix,
                    "duree_incubation_jours": duree,
                    "icone": icone,
                    "actif": True
                },
            )
            if not cree:
                # On s'assure que les valeurs sont les bonnes même si l'objet existait
                espece.prix_unitaire = prix
                espece.duree_incubation_jours = duree
                if not espece.icone:
                    espece.icone = icone
                espece.actif = True
                espece.save()

            self.stdout.write(self.style.SUCCESS(f"{espece.nom} : OK"))

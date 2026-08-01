import uuid
from datetime import timedelta, date
from django.conf import settings
from django.db import models
from django.utils import timezone

class Espece(models.Model):
    nom = models.CharField(max_length=50, unique=True)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)
    duree_incubation_jours = models.PositiveIntegerField(
        help_text="Nombre de jours entre le dépôt et l'éclosion prévue (DPE)."
    )
    icone = models.ImageField(upload_to="icones_especes/", blank=True, null=True)
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Espèce"
        verbose_name_plural = "Espèces"
        ordering = ["nom"]

    def __str__(self):
        return self.nom

class Client(models.Model):
    nom = models.CharField(max_length=150, unique=True)
    telephone = models.CharField(max_length=30, blank=True)
    notes = models.TextField(blank=True)
    est_interne = models.BooleanField(
        default=False,
        help_text="Client interne (M/M), les dépôts sont considérés comme soldés."
    )

    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"
        ordering = ["nom"]

    def __str__(self):
        return self.nom

class ParametresApplication(models.Model):
    nom_etablissement = models.CharField(max_length=150, default="Ma Couveuse")
    logo = models.ImageField(upload_to="branding/", blank=True, null=True)
    fond_ecran = models.ImageField(upload_to="branding/", blank=True, null=True)
    jours_avant_mirage = models.PositiveIntegerField(default=7)
    seuil_alerte_jours = models.PositiveIntegerField(default=3)

    class Meta:
        verbose_name = "Paramètres"
        verbose_name_plural = "Paramètres"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def charger(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

class Depot(models.Model):
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="depots")
    espece = models.ForeignKey(Espece, on_delete=models.PROTECT, related_name="depots")
    date_depot = models.DateField(verbose_name="Date de dépôt")
    quantite = models.PositiveIntegerField(verbose_name="Qté")
    resultat_mirage = models.PositiveIntegerField(null=True, blank=True, verbose_name="RAM")
    date_mirage_effectue = models.DateField(null=True, blank=True, verbose_name="Date réelle mirage")
    nombre_eclos = models.PositiveIntegerField(null=True, blank=True, verbose_name="Éclos")
    date_eclosion_effectuee = models.DateField(null=True, blank=True, verbose_name="Date réelle éclosion")
    prix_unitaire_applique = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    acompte = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    remise = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Remise")
    paiement_solde = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Dépôt"
        verbose_name_plural = "Dépôts"
        ordering = ["-date_depot"]

    def save(self, *args, **kwargs):
        # Fixation du prix au moment du dépôt
        if not self.prix_unitaire_applique:
            self.prix_unitaire_applique = self.espece.prix_unitaire

        # Logique de paiement échelonné : on cumule l'acompte dans le solde payé
        if self.acompte > 0:
            self.paiement_solde += self.acompte
            self.acompte = 0

        # Un client interne solde automatiquement son dépôt
        if self.client.est_interne:
            self.paiement_solde = self.montant_total
            self.acompte = 0
            self.remise = 0

        super().save(*args, **kwargs)

    @property
    def date_mirage(self):
        jours = ParametresApplication.charger().jours_avant_mirage
        return self.date_depot + timedelta(days=jours)

    @property
    def date_prevue_eclosion(self):
        return self.date_depot + timedelta(days=self.espece.duree_incubation_jours)

    @property
    def jours_restants(self):
        aujourd_hui = timezone.localdate()
        dpe = self.date_prevue_eclosion
        if aujourd_hui >= dpe: return "ok"
        return (dpe - aujourd_hui).days

    @property
    def alerte_eclosion_proche(self):
        jr = self.jours_restants
        if jr == "ok": return True  # Reste en alerte si la date est atteinte ou dépassée
        seuil = ParametresApplication.charger().seuil_alerte_jours
        return isinstance(jr, int) and jr <= seuil

    @property
    def alerte_mirage_du_jour(self):
        return self.resultat_mirage is None and timezone.localdate() >= self.date_mirage

    @property
    def montant_total(self):
        return (self.prix_unitaire_applique or 0) * self.quantite

    @property
    def reste_a_payer(self):
        return self.montant_total - self.acompte - self.paiement_solde - self.remise

class MediaBibliotheque(models.Model):
    titre = models.CharField(max_length=150)
    fichier = models.ImageField(upload_to="bibliotheque/")
    ajoute_le = models.DateTimeField(auto_now_add=True)

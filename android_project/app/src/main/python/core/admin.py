from django.contrib import admin
from .models import Espece, Client, Depot, ParametresApplication, MediaBibliotheque


@admin.register(Espece)
class EspeceAdmin(admin.ModelAdmin):
    list_display = ("nom", "prix_unitaire", "duree_incubation_jours", "actif")
    list_editable = ("prix_unitaire", "duree_incubation_jours", "actif")
    search_fields = ("nom",)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("nom", "telephone", "est_interne")
    list_editable = ("telephone", "est_interne")
    search_fields = ("nom",)


@admin.register(Depot)
class DepotAdmin(admin.ModelAdmin):
    list_display = (
        "date_depot", "client", "espece", "quantite",
        "resultat_mirage", "nombre_eclos", "montant_total", "reste_a_payer",
    )
    list_filter = ("espece", "client")
    search_fields = ("client__nom",)
    date_hierarchy = "date_depot"


@admin.register(ParametresApplication)
class ParametresApplicationAdmin(admin.ModelAdmin):
    list_display = ("nom_etablissement", "jours_avant_mirage", "seuil_alerte_jours")

    def has_add_permission(self, request):
        # Singleton : une seule ligne de paramètres.
        return not ParametresApplication.objects.exists()


@admin.register(MediaBibliotheque)
class MediaBibliothequeAdmin(admin.ModelAdmin):
    list_display = ("titre", "ajoute_le")



import os
import json
import urllib.request
import urllib.error
from datetime import datetime
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.db.models import Sum, Count, F, ExpressionWrapper, FloatField

from .forms import (
    CreationCompteAdminForm, ActivationLicenceForm, DemandeActivationForm,
    DepotForm, ClientRapideForm, MediaUploadForm, ParametresForm,
)
from .models import Depot, Client, Espece, ParametresApplication, MediaBibliotheque
from .licence_utils import check_license, save_license, get_license_info, get_display_id
from .translation_strings import get_strings

# ---------------------------------------------------------------------------
# Setup & Licence
# ---------------------------------------------------------------------------

def activation_licence(request):
    if check_license():
        return redirect("dashboard")
    if request.method == "POST":
        form_cle = ActivationLicenceForm(request.POST)
        if form_cle.is_valid():
            if save_license(form_cle.cleaned_data["cle"]):
                messages.success(request, "✅ Licence activée.")
                return redirect("dashboard")
            form_cle.add_error("cle", "Clé invalide.")
    else:
        form_cle = ActivationLicenceForm()
    return render(request, "core/activation_licence.html", {
        "form_cle": form_cle,
        "form_demande": DemandeActivationForm(),
        "machine_id": get_display_id()
    })

URL_SERVEUR_KIS = "https://kissima.pythonanywhere.com/api/v1/activate/"

@require_http_methods(["POST"])
def htmx_verifier_activation(request):
    nom = request.POST.get("nom", "").strip()
    telephone = request.POST.get("telephone", "").strip()
    machine_id = get_display_id()
    payload = {"machine_id": machine_id, "nom": nom, "telephone": telephone, "produit": "KIS Couveuse"}
    try:
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(URL_SERVEUR_KIS, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            if res_data.get("status") == "success":
                if save_license(res_data.get("licence")):
                    return HttpResponse('<script>window.location.href="/"</script>')
            csrf_token = get_token(request)
            return HttpResponse(f'<div class="alert alert-warning">Paiement en attente...<button class="btn btn-primary btn-sm" hx-post="{reverse("htmx_verifier_activation")}" hx-vals=\'{{"nom":"{nom}","telephone":"{telephone}"}}\' hx-target="#activation-form-container">Vérifier</button></div>')
    except Exception as e:
        return HttpResponse(f"Erreur: {e}")

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
    depots_actifs = Depot.objects.filter(nombre_eclos__isnull=True)
    alertes_mirage = [d for d in depots_actifs if d.alerte_mirage_du_jour]
    alertes_eclosion = [d for d in depots_actifs if d.alerte_eclosion_proche]
    return render(request, "core/dashboard.html", {
        "aujourd_hui": timezone.localdate(),
        "alertes_mirage": alertes_mirage,
        "alertes_eclosion": alertes_eclosion,
        "total_depots_actifs": depots_actifs.count(),
        "parametres_globaux": ParametresApplication.charger(),
        "licence": get_license_info(),
        "txt": get_strings()
    })

# ---------------------------------------------------------------------------
# Dépôts
# ---------------------------------------------------------------------------

@login_required
def depot_liste(request):
    depots = Depot.objects.select_related("client", "espece").all()
    # Filtrage simplifié pour la restauration
    q_client = request.GET.get("client", "")
    if q_client: depots = depots.filter(client__nom__icontains=q_client)
    return render(request, "core/depot_list.html", {
        "depots": depots,
        "especes": Espece.objects.filter(actif=True),
        "txt": get_strings()
    })

@login_required
def depot_creer(request):
    if request.method == "POST":
        form = DepotForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("depot_liste")
    else: form = DepotForm()
    return render(request, "core/depot_form.html", {"form": form, "titre": "Nouveau dépôt", "txt": get_strings()})

@login_required
def depot_modifier(request, pk):
    depot = get_object_or_404(Depot, pk=pk)
    if request.method == "POST":
        form = DepotForm(request.POST, instance=depot)
        if form.is_valid():
            form.save()
            return redirect("depot_liste")
    else: form = DepotForm(instance=depot)
    return render(request, "core/depot_form.html", {"form": form, "titre": "Modifier", "depot": depot, "txt": get_strings()})

@login_required
@require_http_methods(["POST"])
def depot_supprimer(request, pk):
    get_object_or_404(Depot, pk=pk).delete()
    return redirect("depot_liste")

# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------

@login_required
def client_list(request):
    return render(request, "core/client_list.html", {"clients": Client.objects.all(), "txt": get_strings()})

@login_required
def client_creer(request):
    if request.method == "POST":
        Client.objects.create(nom=request.POST.get("nom"), telephone=request.POST.get("telephone"))
        return redirect("client_list")
    return render(request, "core/client_form.html", {"txt": get_strings()})

@login_required
def client_bilan(request, pk):
    client = get_object_or_404(Client, pk=pk)
    depots = client.depots.all()
    total_oeufs = depots.aggregate(s=Sum("quantite"))["s"] or 0
    total_eclos = depots.aggregate(s=Sum("nombre_eclos"))["s"] or 0
    taux = round((total_eclos / total_oeufs * 100), 1) if total_oeufs > 0 else 0
    return render(request, "core/client_bilan.html", {
        "client": client, "depots": depots, "total_oeufs": total_oeufs,
        "total_eclos": total_eclos, "taux_reussite": taux, "txt": get_strings(),
        "parametres_globaux": ParametresApplication.charger()
    })

# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

@login_required
def stats(request):
    depots_finis = Depot.objects.filter(nombre_eclos__isnull=False)
    total_ram = depots_finis.aggregate(s=Sum("resultat_mirage"))["s"] or 0
    total_eclos = depots_finis.aggregate(s=Sum("nombre_eclos"))["s"] or 0
    taux = round((total_eclos / total_ram * 100), 1) if total_ram > 0 else 0

    total_gains = Depot.objects.aggregate(s=Sum(F("acompte") + F("paiement_solde")))["s"] or 0
    ca = Depot.objects.aggregate(s=Sum(F("prix_unitaire_applique") * F("quantite") - F("remise")))["s"] or 0

    return render(request, "core/stats.html", {
        "taux_global": taux, "total_gains": total_gains, "chiffre_affaire": ca,
        "total_ram": total_ram, "total_eclos": total_eclos, "txt": get_strings(),
        "classement_clients": Client.objects.annotate(total_depose=Count("depots")).order_by("-total_depose")[:10]
    })

# ---------------------------------------------------------------------------
# Administration & Médias
# ---------------------------------------------------------------------------

@login_required
def gestion_medias(request):
    params = ParametresApplication.charger()
    return render(request, "core/asset_manager.html", {"parametres": params, "txt": get_strings()})

# Placeholders pour les fonctions non encore totalement reconstruites
def export_stats_global_pdf(request): return HttpResponse("Export PDF...")
def export_client_pdf(request, pk): return HttpResponse("Export PDF...")
def whatsapp_situation(request, pk): return HttpResponse("WhatsApp...")
def espece_list(request): return HttpResponse("Espèces...")
def espece_form(request, pk=None): return HttpResponse("Espèce form...")
def client_modifier(request, pk): return HttpResponse("Modifier client...")
def creation_compte_admin(request): return redirect("dashboard")
class ConnexionView(LoginView): template_name = "core/login.html"


# ---------------------------------------------------------------------------
# Vues additionnelles (routes référencées par les templates, complétées ici)
# ---------------------------------------------------------------------------

def client_liste(request):
    """Alias de client_list, nom utilisé par les templates."""
    return client_list(request)


def espece_liste(request):
    """Alias de espece_list, nom utilisé par les templates."""
    return espece_list(request)


def client_creer_rapide(request):
    """Création rapide d'un client depuis le formulaire de dépôt (HTMX)."""
    if request.method == "POST":
        form = ClientRapideForm(request.POST)
        if form.is_valid():
            client = Client.objects.create(
                nom=form.cleaned_data["nom"],
                telephone=form.cleaned_data.get("telephone", ""),
                notes=form.cleaned_data.get("notes", ""),
            )
            return JsonResponse({"id": client.id, "nom": client.nom})
        return JsonResponse({"errors": form.errors}, status=400)
    return HttpResponse(status=405)


def espece_supprimer(request, pk):
    """Désactive une espèce plutôt que de la supprimer (préserve l'historique)."""
    espece = get_object_or_404(Espece, pk=pk)
    espece.actif = False
    espece.save()
    messages.success(request, f"Espèce '{espece.nom}' désactivée.")
    return redirect("espece_liste")


def media_supprimer(request, pk):
    """Supprime un média de la bibliothèque."""
    media = get_object_or_404(MediaBibliotheque, pk=pk)
    media.delete()
    messages.success(request, "Média supprimé.")
    return redirect("gestion_medias")


def whatsapp_alerte_depot(request, pk):
    """Génère un lien WhatsApp d'alerte pour un dépôt spécifique."""
    depot = get_object_or_404(Depot, pk=pk)
    message = f"Bonjour {depot.client.nom}, votre dépôt du {depot.date_depot} nécessite votre attention."
    lien = f"https://wa.me/?text={message}"
    return redirect(lien)


def changer_langue(request):
    """Change la langue active de l'interface (stockée en session)."""
    langue = request.GET.get("langue", "fr")
    if langue not in ("fr", "en", "ar", "es"):
        langue = "fr"
    request.session["langue"] = langue
    return redirect(request.META.get("HTTP_REFERER", "/"))


def liste_sauvegardes(request):
    """Liste des sauvegardes disponibles. Fonctionnalité minimale en attendant
    l'implémentation complète (export SQLite planifié)."""
    return render(request, "core/liste_sauvegardes.html", {"sauvegardes": []})


def creer_sauvegarde(request):
    messages.info(request, "Fonctionnalité de sauvegarde en cours de développement.")
    return redirect("liste_sauvegardes")


def supprimer_sauvegarde(request, pk):
    messages.info(request, "Fonctionnalité de sauvegarde en cours de développement.")
    return redirect("liste_sauvegardes")


def restaurer_sauvegarde(request, pk):
    messages.info(request, "Fonctionnalité de restauration en cours de développement.")
    return redirect("liste_sauvegardes")


def exporter_cloud(request):
    messages.info(request, "Export cloud en cours de développement.")
    return redirect("dashboard")


def importer_cloud(request):
    messages.info(request, "Import cloud en cours de développement.")
    return redirect("dashboard")

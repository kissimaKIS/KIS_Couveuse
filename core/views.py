import os
import json
import urllib.request
import urllib.error
import shutil
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
from django.views.decorators.http import require_http_methods, require_POST
from django.db.models import Sum, Count, F, Q
from django.conf import settings

from .forms import (
    CreationCompteAdminForm, ActivationLicenceForm, DemandeActivationForm,
    DepotForm, ClientForm, ClientRapideForm, EspeceForm, MediaUploadForm, ParametresForm,
)
from .models import Depot, Client, Espece, ParametresApplication, MediaBibliotheque
from .licence_utils import check_license, save_license, get_license_info, get_display_id, get_machine_id
from .translation_strings import get_strings

# ---------------------------------------------------------------------------
# Setup & Licence
# ---------------------------------------------------------------------------

def activation_licence(request):
    if check_license():
        return redirect("dashboard")

    if request.method == "POST":
        action = request.POST.get('action')
        if action == 'activate_key':
            key = request.POST.get('license_key', '').strip().upper()
            if save_license(key):
                messages.success(request, "✅ Application activée avec succès !")
                return redirect('dashboard')
            else:
                messages.error(request, "❌ Clé de licence invalide pour cet appareil.")

    context = {
        'machine_id': get_display_id(),
        'est_gerant': False,
    }
    return render(request, "core/activation_licence.html", context)


URL_SERVEUR_KIS = "https://kissima.pythonanywhere.com/api/v1/activate/"

@require_POST
def htmx_verifier_activation(request):
    nom = request.POST.get("nom", "").strip()
    telephone = request.POST.get("telephone", "").strip()
    machine_id = get_machine_id()
    payload = {"machine_id": machine_id, "nom": nom, "telephone": telephone, "produit": "KIS Couveuse"}
    try:
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(URL_SERVEUR_KIS, data=data, headers=headers, method="POST")
        csrf_token = get_token(request)
        with urllib.request.urlopen(req, timeout=10) as response:
            status_code = response.getcode()
            res_data = json.loads(response.read().decode("utf-8"))
            if status_code == 200 and res_data.get("status") == "success":
                if save_license(res_data.get("licence")):
                    return HttpResponse('<script>window.location.href="/"</script>')
            return HttpResponse(
                f'<div class="space-y-6 animate-fade-in">'
                f'   <div class="bg-blue-900/30 border border-blue-700/50 p-4 rounded-2xl">'
                f'       <p class="text-blue-200 text-[10px] font-bold uppercase mb-3 text-center tracking-widest">Étape 2 : Règlement</p>'
                f'       <div class="space-y-2 text-xs text-blue-100/80 leading-relaxed text-center">'
                f'           <p>Payez via Orange Money / Moov / Wave au <b>76 41 36 30</b></p>'
                f'       </div>'
                f'   </div>'
                f'   <form hx-post="{reverse("htmx_verifier_activation")}" hx-target="#activation-form-container" hx-swap="innerHTML" class="space-y-4">'
                f'       <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}">'
                f'       <input type="hidden" name="nom" value="{nom}">'
                f'       <input type="hidden" name="telephone" value="{telephone}">'
                f'       <button type="submit" class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-4 rounded-xl flex items-center justify-center gap-2">'
                f'           <span>Vérifier mon paiement</span>'
                f'           <div class="htmx-indicator animate-spin h-4 w-4 border-2 border-white/30 border-t-white rounded-full"></div>'
                f'       </button>'
                f'   </form>'
                f'</div>'
            )
    except Exception as e:
        return HttpResponse(f"Erreur: {e}")

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
    lang = request.session.get('django_language', 'fr')
    strings = get_strings(lang)

    depots_actifs = Depot.objects.filter(nombre_eclos__isnull=True).select_related('client', 'espece')
    alertes_mirage = [d for d in depots_actifs if d.alerte_mirage_du_jour]
    alertes_eclosion = [d for d in depots_actifs if d.alerte_eclosion_proche]

    especes = Espece.objects.filter(actif=True)
    for e in especes:
        e.nom_traduit = strings.get(f"sp_{e.nom}", e.nom)

    return render(request, "core/dashboard.html", {
        "aujourd_hui": timezone.localdate(),
        "total_depots_actifs": depots_actifs.count(),
        "alertes_mirage_count": len(alertes_mirage),
        "alertes_eclosion_count": len(alertes_eclosion),
        "especes": especes,
        "parametres_globaux": ParametresApplication.charger(),
        "licence": get_license_info(),
    })

# ---------------------------------------------------------------------------
# Dépôts
# ---------------------------------------------------------------------------

def _get_especes_data_json(lang='fr'):
    return json.dumps({str(e.id): float(e.prix_unitaire) for e in Espece.objects.filter(actif=True)})

@login_required
def depot_liste(request):
    lang = request.session.get('django_language', 'fr')
    strings = get_strings(lang)
    depots = Depot.objects.select_related("client", "espece").all()
    q_client = request.GET.get("client", "")
    if q_client: depots = depots.filter(client__nom__icontains=q_client)

    filter_type = request.GET.get("filter")
    if filter_type == "actifs":
        depots = depots.filter(nombre_eclos__isnull=True)
    elif filter_type == "mirage":
        depots = [d for d in depots if d.alerte_mirage_du_jour]
    elif filter_type == "eclosion":
        depots = [d for d in depots if d.alerte_eclosion_proche]

    for d in depots:
        d.espece.nom_traduit = strings.get(f"sp_{d.espece.nom}", d.espece.nom)

    return render(request, "core/depot_list.html", {"depots": depots, "especes": Espece.objects.filter(actif=True)})

@login_required
def depot_creer(request):
    lang = request.session.get('django_language', 'fr')
    if request.method == "POST":
        form = DepotForm(request.POST, lang=lang)
        if form.is_valid():
            form.save()
            messages.success(request, get_strings(lang)['success_saved'])
            return redirect("dashboard")
    else:
        initial = {"date_depot": timezone.localdate()}
        if request.GET.get("espece"): initial['espece'] = request.GET.get("espece")
        if request.GET.get("client_id"): initial['client'] = request.GET.get("client_id")
        form = DepotForm(initial=initial, lang=lang)

    return render(request, "core/depot_form.html", {
        "form": form, "titre": get_strings(lang)['new_plan'], "especes_data": _get_especes_data_json(lang)
    })

@login_required
def depot_modifier(request, pk):
    lang = request.session.get('django_language', 'fr')
    depot = get_object_or_404(Depot, pk=pk)
    if request.method == "POST":
        form = DepotForm(request.POST, instance=depot, lang=lang)
        if form.is_valid():
            form.save()
            messages.success(request, get_strings(lang)['success_updated'])
            return redirect("dashboard")
    else:
        form = DepotForm(instance=depot, lang=lang)

    return render(request, "core/depot_form.html", {
        "form": form, "titre": get_strings(lang)['edit'], "depot": depot, "especes_data": _get_especes_data_json(lang)
    })

@login_required
@require_http_methods(["POST"])
def depot_supprimer(request, pk):
    lang = request.session.get('django_language', 'fr')
    get_object_or_404(Depot, pk=pk).delete()
    messages.success(request, get_strings(lang)['success_deleted'])
    return redirect("depot_liste")

# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------

@login_required
def client_list(request):
    return render(request, "core/client_list.html", {"clients": Client.objects.all()})

@login_required
def client_creer(request):
    if request.method == "POST":
        form = ClientForm(request.POST)
        if form.is_valid():
            nom = form.cleaned_data["nom"].strip()
            if Client.objects.filter(nom__iexact=nom).exists():
                messages.error(request, f"Le client '{nom}' existe déjà.")
            else:
                client = form.save()
                messages.success(request, f"Client '{nom}' créé avec succès.")
                return redirect(reverse("depot_creer") + f"?client_id={client.pk}")
    else:
        form = ClientForm()
    return render(request, "core/client_form.html", {"form": form, "titre": "Nouveau client"})

@login_required
def client_modifier(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == "POST":
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, "Client mis à jour.")
            return redirect("client_liste")
    else:
        form = ClientForm(instance=client)
    return render(request, "core/client_form.html", {"form": form, "titre": "Modifier client"})

@login_required
def client_bilan(request, pk):
    lang = request.session.get('django_language', 'fr')
    strings = get_strings(lang)
    client = get_object_or_404(Client, pk=pk)
    depots = client.depots.all().select_related('espece')
    total_oeufs = depots.aggregate(s=Sum("quantite"))["s"] or 0
    total_eclos = depots.aggregate(s=Sum("nombre_eclos"))["s"] or 0
    taux = round((total_eclos / total_oeufs * 100), 1) if total_oeufs > 0 else 0

    for d in depots:
        d.espece.nom_traduit = strings.get(f"sp_{d.espece.nom}", d.espece.nom)

    context = {
        "client": client, "depots": depots, "total_oeufs": total_oeufs,
        "total_eclos": total_eclos, "taux_reussite": taux,
        "parametres_globaux": ParametresApplication.charger(),
        "auto_print": request.GET.get('print') == '1'
    }
    return render(request, "core/client_bilan.html", context)

@login_required
def whatsapp_situation(request, pk):
    lang = request.session.get('django_language', 'fr')
    strings = get_strings(lang)
    client = get_object_or_404(Client, pk=pk)

    msg = f"*{strings['wa_msg_prefix']} {client.nom}*\n\n"
    msg += f"{strings['msg_situation']} :\n"

    for d in client.depots.all().order_by("-date_depot"):
        esp_nom = strings.get(f"sp_{d.espece.nom}", d.espece.nom)
        msg += f"\n• {d.date_depot.strftime('%d/%m/%Y')} - {esp_nom}\n"
        msg += f"  - {strings['wa_msg_qty']}: {d.quantite}\n"
        if d.resultat_mirage is not None:
            msg += f"  - {strings['wa_msg_ram']}: {d.resultat_mirage}\n"
        if d.nombre_eclos is not None:
            msg += f"  - {strings['wa_msg_eclos']}: {d.nombre_eclos}\n"
        else:
            msg += f"  - {strings['wa_msg_hatch_date']}: {d.date_prevue_eclosion.strftime('%d/%m/%Y')}\n"

    phone = client.telephone.replace(" ", "").replace("+", "")
    url = f"https://wa.me/{phone}?text={urllib.parse.quote(msg)}"
    return redirect(url)

@login_required
def whatsapp_alerte_depot(request, pk):
    lang = request.session.get('django_language', 'fr')
    strings = get_strings(lang)
    depot = get_object_or_404(Depot, pk=pk)

    esp_nom = strings.get(f"sp_{depot.espece.nom}", depot.espece.nom)
    msg = f"*{strings['wa_msg_prefix']} {depot.client.nom}*\n\n"
    msg += f"{strings['wa_msg_depot']} *{esp_nom}* ({depot.date_depot.strftime('%d/%m/%Y')}):\n"
    msg += f"• {strings['wa_msg_qty']}: {depot.quantite}\n"
    if depot.resultat_mirage is not None:
        msg += f"• {strings['wa_msg_ram']}: {depot.resultat_mirage}\n"
    if depot.nombre_eclos is not None:
        msg += f"• {strings['wa_msg_eclos']}: {depot.nombre_eclos}\n"
    else:
        msg += f"• {strings['wa_msg_hatch_date']}: {depot.date_prevue_eclosion.strftime('%d/%m/%Y')}\n"

    phone = depot.client.telephone.replace(" ", "").replace("+", "")
    url = f"https://wa.me/{phone}?text={urllib.parse.quote(msg)}"
    return redirect(url)

@login_required
def export_client_pdf(request, pk):
    return redirect(reverse("client_bilan", args=[pk]) + "?print=1")

@login_required
def export_stats_global_pdf(request):
    return redirect(reverse("statistiques") + "?print=1")

# ---------------------------------------------------------------------------
# Espèces
# ---------------------------------------------------------------------------

@login_required
def espece_list(request):
    lang = request.session.get('django_language', 'fr')
    strings = get_strings(lang)
    especes = Espece.objects.all()
    for e in especes:
        e.nom_traduit = strings.get(f"sp_{e.nom}", e.nom)
    return render(request, "core/espece_list.html", {"especes": especes})

@login_required
def espece_form(request, pk=None):
    lang = request.session.get('django_language', 'fr')
    strings = get_strings(lang)
    espece = get_object_or_404(Espece, pk=pk) if pk else None

    if request.method == "POST":
        form = EspeceForm(request.POST, request.FILES, instance=espece)
        if form.is_valid():
            form.save()
            messages.success(request, strings['success_saved'] if not pk else strings['success_updated'])
            return redirect("espece_liste")
    else:
        form = EspeceForm(instance=espece)

    titre = strings['edit'] if pk else strings['add']
    return render(request, "core/espece_form.html", {"form": form, "espece": espece, "titre": titre})

@login_required
@require_http_methods(["POST"])
def espece_supprimer(request, pk):
    get_object_or_404(Espece, pk=pk).delete()
    return redirect("espece_liste")

# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

@login_required
def stats(request):
    lang = request.session.get('django_language', 'fr')
    strings = get_strings(lang)

    depots_finis = Depot.objects.filter(nombre_eclos__isnull=False).select_related('espece')
    total_ram = depots_finis.aggregate(s=Sum("resultat_mirage"))["s"] or 0
    total_eclos = depots_finis.aggregate(s=Sum("nombre_eclos"))["s"] or 0
    taux = round((total_eclos / total_ram * 100), 1) if total_ram > 0 else 0

    # EXCLUSION DES CLIENTS INTERNES POUR LES STATS FINANCIÈRES
    depots_commerciaux = Depot.objects.filter(client__est_interne=False)
    total_gains = depots_commerciaux.aggregate(s=Sum(F("paiement_solde")))["s"] or 0
    ca = sum(d.montant_total - d.remise for d in depots_commerciaux)

    # Calcul des meilleurs clients par gain (Limité à 5)
    classement = Client.objects.filter(est_interne=False).annotate(
        gain=Sum('depots__paiement_solde')
    ).filter(gain__gt=0).order_by('-gain')[:5]

    # Calcul des stats par espèces
    data_esp = []
    labels_esp = []
    for esp in Espece.objects.filter(actif=True):
        finis = esp.depots.filter(nombre_eclos__isnull=False)
        ram = finis.aggregate(s=Sum("resultat_mirage"))["s"] or 0
        eclos = finis.aggregate(s=Sum("nombre_eclos"))["s"] or 0
        t = round((eclos / ram * 100), 1) if ram > 0 else 0
        data_esp.append(t)
        labels_esp.append(strings.get(f"sp_{esp.nom}", esp.nom))

    return render(request, "core/stats.html", {
        "taux_global": taux, "total_gains": total_gains, "chiffre_affaire": ca,
        "total_ram": total_ram, "total_eclos": total_eclos,
        "classement_clients": classement,
        "data_especes": data_esp, "labels_especes": labels_esp,
        "auto_print": request.GET.get('print') == '1'
    })

# ---------------------------------------------------------------------------
# Administration & Médias & Sauvegardes
# ---------------------------------------------------------------------------

@login_required
def gestion_medias(request):
    lang = request.session.get('django_language', 'fr')
    params = ParametresApplication.charger()
    if request.method == "POST":
        if "enregistrer_parametres" in request.POST:
            form = ParametresForm(request.POST, request.FILES, instance=params)
            if form.is_valid():
                form.save()
                messages.success(request, get_strings(lang)['success_updated'])
                return redirect("dashboard")
        elif "ajouter_media" in request.POST:
            form = MediaUploadForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                messages.success(request, get_strings(lang)['success_saved'])
        return redirect("gestion_medias")
    return render(request, "core/asset_manager.html", {
        "parametres": params, "form_parametres": ParametresForm(instance=params),
        "form_media": MediaUploadForm(), "images": MediaBibliotheque.objects.all(),
    })

@login_required
def liste_sauvegardes(request):
    backup_dir = os.path.join(os.environ.get("COUVEUSE_MOBILE_BASE_DIR", settings.BASE_DIR), "sauvegardes")
    sauvegardes = []
    if os.path.exists(backup_dir):
        for f in os.listdir(backup_dir):
            if f.endswith(".sqlite3"):
                path = os.path.join(backup_dir, f)
                stat = os.stat(path)
                sauvegardes.append({
                    "nom": f, "date": datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M"),
                    "taille": round(stat.st_size / 1024, 1)
                })
    return render(request, "core/backup_list.html", {"sauvegardes": sauvegardes})

@login_required
def changer_langue(request):
    langue = request.GET.get('langue', 'fr')
    if langue in ['fr', 'en', 'es', 'ar']:
        request.session['django_language'] = langue
    return redirect(request.META.get("HTTP_REFERER", "/"))

@login_required
def a_propos(request):
    return render(request, "core/a_propos.html", {"licence": get_license_info()})

@login_required
@require_POST
def supprimer_sauvegarde(request, nom):
    backup_dir = os.path.join(os.environ.get("COUVEUSE_MOBILE_BASE_DIR", settings.BASE_DIR), "sauvegardes")
    path = os.path.join(backup_dir, nom)
    if os.path.exists(path) and nom.endswith(".sqlite3"):
        os.remove(path)
        messages.success(request, f"Sauvegarde {nom} supprimée.")
    return redirect("liste_sauvegardes")

@login_required
@require_http_methods(["POST"])
def media_supprimer(request, pk):
    get_object_or_404(MediaBibliotheque, pk=pk).delete()
    return redirect("gestion_medias")

def importer_cloud(request):
    if request.method == "POST" and request.FILES.get("fichier_db"):
        f = request.FILES["fichier_db"]
        dest = os.path.join(os.environ.get("COUVEUSE_MOBILE_BASE_DIR", settings.BASE_DIR), "couveuse_mobile.sqlite3")
        with open(dest, 'wb+') as destination:
            for chunk in f.chunks(): destination.write(chunk)
        from django.core.management import call_command
        try: call_command("migrate", interactive=False)
        except Exception: pass
        messages.success(request, "Base de données restaurée. Veuillez relancer l'application.")
    return redirect("liste_sauvegardes")

def restaurer_sauvegarde(request, nom):
    backup_dir = os.path.join(os.environ.get("COUVEUSE_MOBILE_BASE_DIR", settings.BASE_DIR), "sauvegardes")
    source = os.path.join(backup_dir, nom)
    if os.path.exists(source):
        dest = os.path.join(os.environ.get("COUVEUSE_MOBILE_BASE_DIR", settings.BASE_DIR), "couveuse_mobile.sqlite3")
        shutil.copy2(source, dest)
        from django.core.management import call_command
        try: call_command("migrate", interactive=False)
        except Exception: pass
        messages.success(request, f"Sauvegarde {nom} restaurée. Veuillez relancer l'application.")
    return redirect("liste_sauvegardes")

@login_required
def exporter_cloud(request):
    """Génère un lien de téléchargement vers la base de données actuelle pour partage Android."""
    source = os.path.join(os.environ.get("COUVEUSE_MOBILE_BASE_DIR", settings.BASE_DIR), "couveuse_mobile.sqlite3")
    if os.path.exists(source):
        with open(source, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/x-sqlite3')
            response['Content-Disposition'] = 'attachment; filename="sauvegarde_couveuse.sqlite3"'
            return response
    messages.error(request, "Fichier de base de données introuvable.")
    return redirect("liste_sauvegardes")

@login_required
def rapport_global(request):
    """Page de rapport complet avec filtres et graphiques."""
    depots = Depot.objects.select_related('client', 'espece').all()

    # Filtres
    q_client = request.GET.get('client')
    if q_client: depots = depots.filter(client_id=q_client)

    q_espece = request.GET.get('espece')
    if q_espece: depots = depots.filter(espece_id=q_espece)

    date_debut = request.GET.get('date_debut')
    if date_debut: depots = depots.filter(date_depot__gte=date_debut)

    date_fin = request.GET.get('date_fin')
    if date_fin: depots = depots.filter(date_depot__lte=date_fin)

    # Stats
    total_oeufs = depots.aggregate(s=Sum('quantite'))['s'] or 0
    total_eclos = depots.aggregate(s=Sum('nombre_eclos'))['s'] or 0
    taux = round((total_eclos / total_oeufs * 100), 1) if total_oeufs > 0 else 0

    # Financier (Hors internes)
    depots_payants = depots.filter(client__est_interne=False)
    total_revenue = depots_payants.aggregate(s=Sum('paiement_solde'))['s'] or 0
    total_ca = sum(d.montant_total - d.remise for d in depots_payants)

    context = {
        "depots": depots, "total_oeufs": total_oeufs, "total_eclos": total_eclos, "taux": taux,
        "total_revenue": total_revenue, "total_ca": total_ca,
        "clients": Client.objects.all(), "especes": Espece.objects.filter(actif=True),
        "auto_print": request.GET.get('print') == '1'
    }
    return render(request, "core/rapport_global.html", context)

def client_creer_rapide(request): return redirect("client_creer")
def creation_compte_admin(request): return redirect("dashboard")
class ConnexionView(LoginView): template_name = "core/login.html"

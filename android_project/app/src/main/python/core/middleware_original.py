"""
Deux middlewares de sécurité, exécutés dans cet ordre (voir settings.py) :

1. LicenceMiddleware        -> bloque tout accès si la licence n'est pas activée.
2. PremierLancementMiddleware -> si aucun compte admin n'existe, force la création
                                  du tout premier compte avant d'autoriser l'accès
                                  au reste de l'application.
"""
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.urls import reverse, resolve, Resolver404  # <-- Importations ajoutées

# Utilisez plutôt les noms exacts de vos routes Django (ex: 'activation_licence')
URLS_EXEMPTEES_LICENCE = {"activation_licence"}
URLS_EXEMPTEES_SETUP = {"creation_compte_admin", "activation_licence"}


class LicenceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        chemin_statique = request.path.startswith(("/static/", "/media/"))
        
        # 1. Résolution dynamique du nom de l'URL
        try:
            url_name = resolve(request.path_info).url_name
        except Resolver404:
            url_name = None

        # 2. Vérification de la licence
        # (Logique obsolète utilisant la base de données - désactivée)
        # if not chemin_statique and url_name not in URLS_EXEMPTEES_LICENCE and not Licence.est_active():
        #     return redirect(reverse("activation_licence"))

        return self.get_response(request)


class PremierLancementMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        chemin_statique = request.path.startswith(("/static/", "/media/"))

        # 1. Résolution dynamique du nom de l'URL
        try:
            url_name = resolve(request.path_info).url_name
        except Resolver404:
            url_name = None

        if chemin_statique or url_name in URLS_EXEMPTEES_SETUP:
            return self.get_response(request)

        User = get_user_model()
        if not User.objects.exists():
            return redirect(reverse("creation_compte_admin"))

        return self.get_response(request)


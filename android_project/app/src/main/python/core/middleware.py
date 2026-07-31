"""
Middlewares de sécurité pour KIS Couveuse.
"""
from django.contrib.auth import get_user_model, login
from django.shortcuts import redirect
from django.urls import reverse, resolve, Resolver404
from .licence_utils import check_license

# Utilisateur par défaut pour l'auto-login sur mobile
DEFAULT_USERNAME = "kis"

URLS_EXEMPTEES_LICENCE = {"activation_licence", "htmx_verifier_activation"}

class LicenceMiddleware:
    """Bloque tout accès si la licence n'est pas activée via licence.dat."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        
        # 1. Chemins toujours autorisés
        if path.startswith(("/static/", "/media/")):
            return self.get_response(request)

        try:
            url_name = resolve(request.path_info).url_name
        except Resolver404:
            url_name = None

        if url_name in URLS_EXEMPTEES_LICENCE:
            return self.get_response(request)

        # 2. Vérification de la licence via licence_utils
        if not check_license():
            return redirect(reverse("activation_licence"))

        return self.get_response(request)


class AutoLoginMiddleware:
    """Connecte automatiquement l'utilisateur unique s'il ne l'est pas déjà."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            User = get_user_model()
            user = User.objects.filter(username=DEFAULT_USERNAME).first()

            if user is None:
                # Si l'utilisateur n'existe pas (ex: après restauration d'une vieille DB),
                # on le recrée immédiatement pour éviter de bloquer l'accès.
                try:
                    user = User.objects.create_superuser(
                        DEFAULT_USERNAME, "kis@kissima.com", "kis_password_2026"
                    )
                except Exception:
                    pass

            if user is not None:
                login(request, user)
                request.user = user

        return self.get_response(request)

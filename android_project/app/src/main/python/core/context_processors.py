from .models import ParametresApplication
from .translation_strings import get_strings

def parametres_globaux(request):
    """Rend les paramètres visuels disponibles dans tous les templates."""
    try:
        return {"parametres_globaux": ParametresApplication.charger()}
    except Exception:
        return {"parametres_globaux": None}

def langue_active(request):
    """Fournit les chaînes de traduction (txt) et l'état RTL au template."""
    # On récupère la langue de la session ou du téléphone
    lang = request.session.get('django_language', 'fr')
    return {
        "txt": get_strings(lang),
        "current_lang": lang,
        "is_rtl": lang == 'ar'
    }

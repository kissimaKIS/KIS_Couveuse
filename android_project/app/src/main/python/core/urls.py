from django.contrib.auth.views import LogoutView
from django.urls import path
from . import views

urlpatterns = [
    path("setup/licence/", views.activation_licence, name="activation_licence"),
    path("setup/licence/verifier/", views.htmx_verifier_activation, name="htmx_verifier_activation"),
    path("connexion/", views.ConnexionView.as_view(), name="login"),
    path("deconnexion/", LogoutView.as_view(next_page="login"), name="logout"),

    path("", views.dashboard, name="dashboard"),
    path("stats/", views.stats, name="statistiques"),
    path("stats/export/global/", views.export_stats_global_pdf, name="export_stats_global_pdf"),

    path("depots/", views.depot_liste, name="depot_liste"),
    path("depots/nouveau/", views.depot_creer, name="depot_creer"),
    path("depots/<int:pk>/modifier/", views.depot_modifier, name="depot_modifier"),
    path("depots/<int:pk>/supprimer/", views.depot_supprimer, name="depot_supprimer"),
    path("depots/<int:pk>/whatsapp/", views.whatsapp_alerte_depot, name="whatsapp_alerte_depot"),

    path("clients/", views.client_list, name="client_liste"),
    path("clients/nouveau/", views.client_creer, name="client_creer"),
    path("clients/nouveau/rapide/", views.client_creer_rapide, name="client_creer_rapide"),
    path("clients/<int:pk>/modifier/", views.client_modifier, name="client_modifier"),
    path("clients/<int:pk>/bilan/", views.client_bilan, name="client_bilan"),
    path("clients/<int:pk>/whatsapp/", views.whatsapp_situation, name="whatsapp_situation"),
    path("clients/<int:pk>/export/pdf/", views.export_client_pdf, name="export_client_pdf"),

    path("especes/", views.espece_list, name="espece_liste"),
    path("especes/nouvelle/", views.espece_form, name="espece_creer"),
    path("especes/<int:pk>/modifier/", views.espece_form, name="espece_modifier"),
    path("especes/<int:pk>/supprimer/", views.espece_supprimer, name="espece_supprimer"),

    path("medias/", views.gestion_medias, name="gestion_medias"),
    path("medias/<int:pk>/supprimer/", views.media_supprimer, name="media_supprimer"),

    path("sauvegardes/", views.liste_sauvegardes, name="liste_sauvegardes"),
    path("sauvegardes/exporter-cloud/", views.exporter_cloud, name="exporter_cloud"),
    path("sauvegardes/importer-cloud/", views.importer_cloud, name="importer_cloud"),
    path("sauvegardes/<str:nom>/restaurer/", views.restaurer_sauvegarde, name="restaurer_sauvegarde"),
    path("sauvegardes/<str:nom>/supprimer/", views.supprimer_sauvegarde, name="supprimer_sauvegarde"),

    path("langue/changer/", views.changer_langue, name="changer_langue"),
    path("a-propos/", views.a_propos, name="a_propos"),
]

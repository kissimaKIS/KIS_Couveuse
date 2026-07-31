from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Depot, Client, Espece, MediaBibliotheque, ParametresApplication
from .translation_strings import get_strings

User = get_user_model()


class CreationCompteAdminForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username",)


class ActivationLicenceForm(forms.Form):
    cle = forms.CharField(
        label="Clé de licence",
        widget=forms.TextInput(attrs={"placeholder": "KIS-XXXX-XXXX-XXXX-XXXXXXXX", "class": "form-control"}),
    )


class DemandeActivationForm(forms.Form):
    nom = forms.CharField(
        label="Nom complet",
        widget=forms.TextInput(attrs={"placeholder": "Ex: Moussa Coulibaly", "class": "form-control"}),
    )
    telephone = forms.CharField(
        label="Téléphone",
        widget=forms.TextInput(attrs={"placeholder": "Ex: 77665544", "class": "form-control"}),
    )


class DepotForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        lang = kwargs.pop('lang', 'fr')
        super().__init__(*args, **kwargs)
        strings = get_strings(lang)
        # Traduction des noms d'espèces dans le menu déroulant
        self.fields['espece'].queryset = Espece.objects.filter(actif=True)
        self.fields['espece'].label_from_instance = lambda obj: strings.get(f"sp_{obj.nom}", obj.nom)

    class Meta:
        model = Depot
        fields = [
            "client", "espece", "date_depot", "quantite",
            "resultat_mirage", "date_mirage_effectue", "nombre_eclos",
            "acompte", "remise", "paiement_solde", "notes",
        ]
        widgets = {
            "date_depot": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "date_mirage_effectue": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "client": forms.Select(attrs={"class": "form-select"}),
            "espece": forms.Select(attrs={"class": "form-select"}),
            "quantite": forms.NumberInput(attrs={"class": "form-control"}),
            "resultat_mirage": forms.NumberInput(attrs={"class": "form-control"}),
            "nombre_eclos": forms.NumberInput(attrs={"class": "form-control"}),
            "acompte": forms.NumberInput(attrs={"class": "form-control"}),
            "remise": forms.NumberInput(attrs={"class": "form-control"}),
            "paiement_solde": forms.NumberInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def save(self, commit=True):
        depot = super().save(commit=False)
        if not depot.prix_unitaire_applique:
            depot.prix_unitaire_applique = depot.espece.prix_unitaire
        if commit:
            depot.save()
        return depot


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ["nom", "telephone", "notes", "est_interne"]
        widgets = {
            "nom": forms.TextInput(attrs={"class": "form-control"}),
            "telephone": forms.TextInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "est_interne": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class ClientRapideForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ["nom", "telephone", "est_interne"]
        widgets = {
            "nom": forms.TextInput(attrs={"class": "form-control"}),
            "telephone": forms.TextInput(attrs={"class": "form-control"}),
            "est_interne": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class MediaUploadForm(forms.ModelForm):
    class Meta:
        model = MediaBibliotheque
        fields = ["titre", "fichier"]
        widgets = {
            "titre": forms.TextInput(attrs={"class": "form-control"}),
            "fichier": forms.FileInput(attrs={"class": "form-control"}),
        }


class ParametresForm(forms.ModelForm):
    class Meta:
        model = ParametresApplication
        fields = [
            "nom_etablissement", "logo", "fond_ecran",
            "jours_avant_mirage", "seuil_alerte_jours",
        ]
        widgets = {
            "nom_etablissement": forms.TextInput(attrs={"class": "form-control"}),
            "logo": forms.FileInput(attrs={"class": "form-control"}),
            "fond_ecran": forms.FileInput(attrs={"class": "form-control"}),
            "jours_avant_mirage": forms.NumberInput(attrs={"class": "form-control"}),
            "seuil_alerte_jours": forms.NumberInput(attrs={"class": "form-control"}),
        }

# Gestion Couveuse — Application Django

Application web (Django + PostgreSQL) qui remplace le fichier Excel de suivi
de couveuse (dépôts d'œufs, mirage, éclosion, paiements). Elle reproduit
fidèlement la logique du fichier d'origine tout en l'automatisant.

## 1. Correspondance Excel → Application

| Colonne Excel | Champ / calcul dans l'application                                   |
|---|---|
| Date (dépôt)   | `Depot.date_depot`                                                    |
| Déposant       | `Depot.client` (FK vers `Client`, liste extensible)                   |
| Type           | `Depot.espece` (FK vers `Espece`, prix + durée éditables sans coder)  |
| Jrs R.         | `Depot.jours_restants` — recalculé à l'affichage, jamais stocké       |
| Qté            | `Depot.quantite`                                                      |
| DM             | `Depot.date_mirage` = dépôt + `jours_avant_mirage` (7 j. par défaut)  |
| RAM            | `Depot.resultat_mirage` (saisie manuelle après mirage physique)       |
| DPE            | `Depot.date_prevue_eclosion` = dépôt + durée d'incubation de l'espèce |
| Éclos          | `Depot.nombre_eclos` (saisie manuelle après éclosion)                 |
| Mtt            | `Depot.montant_total` = prix unitaire figé × quantité                 |
| Rem            | `Depot.acompte`                                                       |
| Payé           | `Depot.paiement_solde`                                                |
| Reste          | `Depot.reste_a_payer` = Mtt − Rem − Payé                              |

**Amélioration par rapport à l'Excel** : les prix unitaires et durées
d'incubation par espèce (qui étaient codés en dur dans des formules `SI()`
imbriquées) sont désormais des lignes éditables du modèle `Espece`,
modifiables depuis l'admin Django sans toucher au code. Le prix appliqué à
un dépôt est **figé au moment de l'enregistrement** (`prix_unitaire_applique`) :
une correction de tarif plus tard ne modifie donc jamais l'historique déjà
facturé, contrairement au fichier Excel où changer une formule recalculait
toutes les lignes existantes.

## 2. Installation (premier déploiement)

```bash
python3 -m venv venv
source venv/bin/activate          # Windows : venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # puis ajustez les identifiants PostgreSQL
createdb couveuse_db              # ou via pgAdmin / psql

python manage.py migrate
python manage.py seed_especes     # précharge les espèces avec prix/durées de l'Excel
python manage.py runserver
```

Ouvrez ensuite `http://127.0.0.1:8000`.

## 3. Premier lancement (dans l'application)

1. **Écran d'activation de licence** : saisissez `KIS-GEST-COUV-2026-0011`.
   Sans cette clé, aucun autre écran n'est accessible.
2. **Création du compte administrateur** : ce formulaire n'apparaît que si
   aucun utilisateur n'existe encore en base — au tout premier démarrage.
3. Vous accédez ensuite au tableau de bord.

## 4. Recherche

Depuis **Dépôts**, un formulaire de recherche permet de filtrer :
- par **nom de client** (recherche partielle),
- par **espèce**,
- par **date de dépôt** *ou* par **date d'éclosion prévue** (au choix, via le
  menu déroulant "Rechercher par"), avec une plage de dates Du / Au.

## 5. Alertes

Le tableau de bord affiche automatiquement :
- **Mirages à effectuer aujourd'hui** : dépôts dont la date de mirage (DM)
  est atteinte ou dépassée et dont le RAM n'a pas encore été saisi.
- **Éclosions proches ou dépassées** : dépôts dont il reste ≤ 3 jours avant
  la date prévue d'éclosion (seuil réglable dans *Médias / apparence*),
  reproduisant la mise en forme conditionnelle `Jrs R. <= 3` du fichier
  Excel d'origine.

Sur mobile (voir `android/README.md`), ces mêmes règles déclenchent des
**notifications natives**, générées par un service qui tourne en
arrière-plan même lorsque l'application n'est pas au premier plan.

## 6. Gestion des médias (logos, icônes, fond d'écran)

Menu **Médias / apparence** : upload du logo, du fond d'écran, et d'images
libres réutilisables (bibliothèque), sans modification de code. Les icônes
par espèce se gèrent depuis l'admin Django (`Espece.icone`).

## 7. Lancement "double-clic" (desktop)

- **Windows** : double-cliquez sur `start.bat`.
- **macOS / Linux** : `./start.sh` (ou double-clic selon la configuration du
  gestionnaire de fichiers).

Ces scripts démarrent PostgreSQL, activent l'environnement virtuel, lancent
`runserver`, puis ouvrent automatiquement le navigateur par défaut.

Pour un exécutable autonome avec icône dans la barre système et dans
l'explorateur Windows (sans même ouvrir de terminal), un fichier `.spec`
prêt à l'emploi est fourni, avec icône personnalisée et métadonnées
Windows :

```bash
build_exe.bat
```

Ce script active le venv, installe PyInstaller si besoin, puis compile via
`GestionCouveuse.spec` (qui référence `icon.ico` et `version_info.txt`).
Le résultat est un exécutable unique : `dist\GestionCouveuse.exe`.

- **`icon.ico`** : icône affichée sur l'exécutable et dans la barre système.
  Une icône par défaut est fournie — remplacez-la par la vôtre (même nom de
  fichier, format `.ico` multi-résolutions) pour personnaliser.
- **`version_info.txt`** : métadonnées Windows (éditeur, version, description)
  visibles dans les propriétés du fichier — modifiez les champs
  `CompanyName`, `FileDescription`, `ProductVersion`, etc. avant de livrer au
  client final.

Le `.env` doit être placé à côté de `GestionCouveuse.exe` (PostgreSQL doit
rester installé sur la machine cible ; PyInstaller n'embarque que le code
Python, pas le serveur de base de données).

## 8. Application Android

Le dossier `android_project/` contient un **projet Android Studio complet et
buildable** (Gradle + plugin Chaquopy déjà configurés) : serveur Django
embarqué directement sur le téléphone (aucune dépendance à un PC), WebView
au rendu identique à la version web, service en premier plan pour tourner en
arrière-plan, et notifications natives de mirage/éclosion.

Étapes rapides :
```bash
python manage.py makemigrations core   # si pas déjà fait
./preparer_projet_android.sh           # ou .bat sous Windows
```
puis ouvrez `android_project/` dans Android Studio et lancez **Run**.
Détails complets dans `android/README.md`.

## 9. PWA (mode hors-ligne partiel)

L'application expose un `manifest.json` et un `service-worker.js`
(`static/pwa/`) : elle peut être "installée" depuis un navigateur mobile ou
desktop et garde en cache la dernière page consultée en cas de coupure
réseau temporaire.

## 10. Structure du projet

```
couveuse_project/          Réglages Django (settings.py, urls.py, settings_mobile.py)
core/                       Application principale
  models.py                 Espece, Client, Depot, ParametresApplication, MediaBibliotheque, Licence
  middleware.py              LicenceMiddleware, PremierLancementMiddleware
  views.py / urls.py / forms.py / admin.py
  management/commands/seed_especes.py
templates/                  Gabarits HTML (Bootstrap 5)
static/                     CSS + manifest/service-worker PWA

start.bat / start.sh        Lancement "double-clic" (dev, via runserver)
desktop_launcher.py         Point d'entrée PyInstaller (icône barre système)
GestionCouveuse.spec        Config PyInstaller (icône, version_info, imports Django)
icon.ico                    Icône de l'exécutable Windows (à remplacer par la vôtre)
version_info.txt            Métadonnées Windows de l'exécutable (éditeur, version...)
build_exe.bat                Compile GestionCouveuse.exe via le .spec

android_project/            Projet Android Studio complet (Gradle + Chaquopy)
android/README.md           Explication détaillée de l'architecture Android
preparer_projet_android.sh   Copie core/couveuse_project/templates/static dans android_project/
preparer_projet_android.bat  (idem, Windows)
```

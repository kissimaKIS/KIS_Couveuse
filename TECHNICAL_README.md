# README Technique - KIS Couveuse Android

Ce document détaille l'architecture et les choix techniques du projet **KIS Couveuse v1.0.0**.

## 1. Architecture Globale
L'application est une solution **Hybride Native/Web** basée sur :
- **Backend** : Django 5.0 (Python 3.12) embarqué via Chaquopy.
- **Frontend** : HTML5 / Bootstrap 5 / Tailwind CSS / Alpine.js / ApexCharts.
- **Mobile Wrapper** : Kotlin (Android Natif) avec WebView.
- **Base de données** : SQLite (version mobile) pour une autonomie totale sans internet.

## 2. Système de Licence
Le module `core/licence_utils.py` gère la sécurité :
- **Hardware ID** : Basé sur le `ANDROID_ID` unique du téléphone.
- **Algorithme** : Signature HMAC-SHA256 combinant l'ID machine, une clé secrète et la date d'expiration.
- **Persistance** : Fichier `licence.dat` stocké dans le stockage interne privé.
- **Validation** : Middleware Django bloquant tout accès (hors média/static) si la licence est absente ou expirée.

## 3. Optimisations Mobiles
- **Foreground/Background Service** : `CouveuseServerService.kt` maintient le serveur Django actif. Il a été passé en mode "invisible" (sans notification) pour la version 1.0.0.
- **Asset Extraction** : `AssetExtractor.kt` gère la synchronisation entre les assets de l'APK et le système de fichiers Android. Le marqueur `.extrait_ok_vXX` permet de forcer la mise à jour des templates tout en préservant la base de données SQLite.
- **Auto-Login** : `AutoLoginMiddleware.py` connecte automatiquement l'utilisateur système `kis` pour supprimer la contrainte de mot de passe sur mobile.

## 4. Gestion des Médias et PDF
- **Rendu PDF** : Utilisation de `CouveuseApp.imprimerPage()` via un `JavascriptInterface`. Cela permet d'utiliser le moteur d'impression natif d'Android (Save to PDF) sans surcharger l'app avec des bibliothèques lourdes comme ReportLab.
- **Images Volailles** : Gérées via le modèle `Espece` avec un fallback sur des icônes Bootstrap si l'image est absente.

## 5. Synchronisation et Build
- **Build Gradle** : Configuré pour inclure toutes les dépendances Python nécessaires (`django`, `pillow`, `python-dotenv`).
- **Version Code** : `3`
- **Version Name** : `1.0.0`

## 6. Structure des fichiers
- `/core` : Logique métier Django (Modèles, Vues, Internationalisation).
- `/templates` : Gabarits HTML partagés entre Web et Android.
- `/static` : Ressources CSS/JS (dont `modern.css` pour le support offline).
- `/android_project` : Projet Android Studio complet.

---
**Développeur** : Madikandé Traoré
**Copyright** : © 2026 KIS SOLUTION

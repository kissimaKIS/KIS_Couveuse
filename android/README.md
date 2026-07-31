# Application Android — Serveur Django embarqué (Chaquopy)

> **Projet Android Studio prêt à l'emploi** : voir `android_project/` à la
> racine du livrable (Gradle + Chaquopy déjà configurés, Kotlin, service en
> arrière-plan, notifications). Étapes concrètes :
>
> 1. Générez les migrations si ce n'est pas fait : `python manage.py makemigrations core`
> 2. Lancez `preparer_projet_android.sh` (ou `.bat`) à la racine : ce script
>    copie automatiquement `core/`, `couveuse_project/`, `templates/` et
>    `static/` aux bons emplacements dans `android_project/`.
> 3. Ouvrez `android_project/` dans Android Studio (avec le SDK Android +
>    NDK installés). Gradle synchronise seul grâce au plugin Chaquopy déjà
>    déclaré dans `build.gradle`.
> 4. Branchez un téléphone (mode développeur + débogage USB) ou lancez un
>    émulateur, puis **Run**.
> 5. Pour distribuer : `./gradlew bundleRelease` (App Bundle signé pour le
>    Play Store) ou `./gradlew assembleRelease` (APK direct).
>
> Le reste de ce document explique le fonctionnement interne de chaque
> pièce (déjà codée dans `android_project/`) : pourquoi un service au
> premier plan, comment les templates Django sont rendus accessibles à
> Django alors qu'ils sont dans l'APK, etc.

Objectif : le serveur Django tourne **directement sur le téléphone**, aucune
dépendance à un PC. L'app Android embarque un interpréteur Python (via
[Chaquopy](https://chaquo.com/chaquopy/)) qui exécute Django, plus un WebView
qui affiche `http://127.0.0.1:8000` — rendu strictement identique à la version
web/desktop puisque c'est la même application Django, les mêmes templates,
le même CSS.

## Vue d'ensemble de l'architecture

```
┌─────────────────────────────────────────────┐
│                 App Android (Kotlin)          │
│                                                │
│  ┌───────────────┐      ┌──────────────────┐ │
│  │ ForegroundServ.│─────▶│ Python (Chaquopy) │ │
│  │ (tourne en     │      │ manage.py runserver│
│  │  arrière-plan) │      │  + SQLite/Postgres │ │
│  └───────────────┘      └────────┬──────────┘ │
│                                    │            │
│  ┌───────────────────────────────▼──────────┐ │
│  │  WebView → http://127.0.0.1:8000          │ │
│  └────────────────────────────────────────────┘│
└─────────────────────────────────────────────┘
```

## 1. Base de données sur mobile

PostgreSQL n'est pas réaliste à embarquer sur Android. Deux options :

- **Recommandé : SQLite** pour la variante mobile (léger, aucun service à
  gérer, Django le supporte nativement). Prévoir un `settings_mobile.py` qui
  bascule `DATABASES["default"]["ENGINE"]` sur
  `django.db.backends.sqlite3`, sans toucher au reste du code — les modèles
  restent identiques.
- Alternative : PostgreSQL embarqué via une distribution statique
  (ex. `libpg_query` compilé pour Android) — nettement plus complexe, à
  réserver si une vraie synchronisation multi-appareils est requise plus tard.

## 2. Dépendances Gradle (`app/build.gradle`)

```gradle
plugins {
    id 'com.android.application'
    id 'com.chaquo.python'
}

android {
    defaultConfig {
        minSdkVersion 26
        ndk { abiFilters "armeabi-v7a", "arm64-v8a", "x86_64" }
        python {
            pip {
                install "django"
                install "pillow"
            }
        }
    }
}
```

## 3. Service en arrière-plan (le point demandé : "tourner en arrière-plan")

Un `ForegroundService` Android maintient le serveur Django actif même quand
l'app est mise en arrière-plan ou que l'écran est éteint — indispensable pour
que les notifications d'alerte (mirage / éclosion, voir §4) continuent de
fonctionner.

```kotlin
// CouveuseServerService.kt
class CouveuseServerService : Service() {
    private lateinit var python: Python

    override fun onCreate() {
        super.onCreate()
        if (!Python.isStarted()) Python.start(AndroidPlatform(this))
        python = Python.getInstance()
        startForeground(1, buildNotification())
        Thread { demarrerServeurDjango() }.start()
    }

    private fun demarrerServeurDjango() {
        val module = python.getModule("mobile_entrypoint")
        module.callAttr("demarrer") // équivalent Python de manage.py migrate + runserver
    }

    private fun buildNotification(): Notification {
        val channelId = "couveuse_service"
        val channel = NotificationChannel(
            channelId, "Service Couveuse", NotificationManager.IMPORTANCE_LOW
        )
        (getSystemService(NotificationManager::class.java)).createNotificationChannel(channel)
        return NotificationCompat.Builder(this, channelId)
            .setContentTitle("Gestion Couveuse")
            .setContentText("Le serveur local est actif")
            .setSmallIcon(R.drawable.ic_notification)
            .build()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
```

`mobile_entrypoint.py` (côté Python, packagé dans `app/src/main/python/` —
version réelle livrée dans `android_project/`) prend en paramètre le
**dossier réel du stockage interne** où `AssetExtractor.kt` a copié
`templates/` et `static/` depuis les assets de l'APK, car Django a besoin
d'un vrai chemin disque pour les lire (il ne peut pas lire directement dans
l'archive APK) :

```python
import os

def _preparer_django(chemin_base):
    os.environ["COUVEUSE_MOBILE_BASE_DIR"] = chemin_base
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "couveuse_project.settings_mobile")
    import django
    django.setup()

def demarrer(chemin_base):
    _preparer_django(chemin_base)
    from django.core.management import call_command
    call_command("migrate", interactive=False)
    from core.models import Espece
    if not Espece.objects.exists():
        call_command("seed_especes")
    call_command("runserver", "127.0.0.1:8000", use_reloader=False)
```

## 4. Alertes mobiles (notifications de mirage / éclosion)

Un `WorkManager` périodique (ex. toutes les heures) interroge en interne les
modèles Django (`Depot.alerte_mirage_du_jour`, `Depot.alerte_eclosion_proche`)
via le même module Python, et déclenche une notification Android native si
au moins une alerte est active — reproduisant côté mobile la mise en forme
conditionnelle `Jrs R. <= 3` de l'Excel d'origine.

```kotlin
class AlerteCouveuseWorker(ctx: Context, params: WorkerParameters) : Worker(ctx, params) {
    override fun doWork(): Result {
        val python = Python.getInstance()
        val alertes = python.getModule("mobile_entrypoint").callAttr("compter_alertes")
        val nbMirage = alertes.asMap()["mirage"]?.toInt() ?: 0
        val nbEclosion = alertes.asMap()["eclosion"]?.toInt() ?: 0
        if (nbMirage > 0 || nbEclosion > 0) {
            envoyerNotification(nbMirage, nbEclosion)
        }
        return Result.success()
    }
}
```

Planification (dans `MainActivity` ou `Application.onCreate`) :

```kotlin
val requete = PeriodicWorkRequestBuilder<AlerteCouveuseWorker>(1, TimeUnit.HOURS).build()
WorkManager.getInstance(context).enqueueUniquePeriodicWork(
    "alerte_couveuse", ExistingPeriodicWorkPolicy.KEEP, requete
)
```

## 5. WebView (`MainActivity.kt`)

```kotlin
class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        startForegroundService(Intent(this, CouveuseServerService::class.java))

        val webView = WebView(this)
        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        setContentView(webView)

        // Attendre que le serveur Django local soit prêt avant de charger la page.
        attendreServeurPuisCharger(webView, "http://127.0.0.1:8000")
    }
}
```

## 6. Permissions (`AndroidManifest.xml`)

```xml
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
<uses-permission android:name="android.permission.INTERNET" />
<!-- INTERNET est nécessaire même en local : le WebView communique par HTTP
     avec 127.0.0.1, ce qui passe par la pile réseau Android. -->
```

## 7. Build de l'APK

```bash
./gradlew assembleRelease
# ou, pour un APK signé prêt à distribuer :
./gradlew bundleRelease
```

## Résumé des points clés

| Exigence du cahier des charges                  | Implémentation                                 |
|---------------------------------------------------|-------------------------------------------------|
| Rendu identique à la version web/desktop           | Même code Django, mêmes templates HTML/CSS      |
| Tourner en arrière-plan                            | `ForegroundService` Android + notification persistante |
| Notifications de mirage / éclosion                 | `WorkManager` périodique + notifications natives |
| Aucune dépendance à un PC                          | Serveur Django + SQLite entièrement embarqués via Chaquopy |

package com.kissima.couveuse

import android.app.Application
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import java.util.concurrent.TimeUnit

class App : Application() {
    override fun onCreate() {
        super.onCreate()

        // Vérifie les alertes mirage/éclosion toutes les heures, même quand
        // l'application n'est pas ouverte, et déclenche une notification.
        val requeteAlerte = PeriodicWorkRequestBuilder<AlerteCouveuseWorker>(1, TimeUnit.HOURS).build()
        WorkManager.getInstance(this).enqueueUniquePeriodicWork(
            "alerte_couveuse",
            ExistingPeriodicWorkPolicy.KEEP,
            requeteAlerte,
        )
    }
}

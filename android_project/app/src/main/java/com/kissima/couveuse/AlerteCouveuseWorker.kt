package com.kissima.couveuse

import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import androidx.core.app.NotificationCompat
import androidx.work.Worker
import androidx.work.WorkerParameters
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform

/**
 * Envoie des notifications périodiques pour les mirages et éclosions.
 */
class AlerteCouveuseWorker(ctx: Context, params: WorkerParameters) : Worker(ctx, params) {

    override fun doWork(): Result {
        try {
            if (!Python.isStarted()) {
                Python.start(AndroidPlatform(applicationContext))
            }
            val python = Python.getInstance()
            val cheminBase = AssetExtractor.extraireSiNecessaire(applicationContext)

            val module = python.getModule("mobile_entrypoint")
            val resultat = module.callAttr("compter_alertes", cheminBase)
            
            val nbMirage = resultat.callAttr("get", "mirage").toInt()
            val nbEclosion = resultat.callAttr("get", "eclosion").toInt()

            if ((nbMirage > 0) || (nbEclosion > 0)) {
                envoyerNotification(nbMirage, nbEclosion)
            }
        } catch (e: Exception) {
            return Result.retry()
        }
        return Result.success()
    }

    private fun envoyerNotification(nbMirage: Int, nbEclosion: Int) {
        val morceaux = mutableListOf<String>()
        if (nbMirage > 0) morceaux.add("$nbMirage mirage(s) à faire")
        if (nbEclosion > 0) morceaux.add("$nbEclosion éclosion(s) proche(s)")
        val texte = morceaux.joinToString(" · ")

        // Action quand on clique sur la notification : Ouvrir l'application de manière fiable
        val intent = applicationContext.packageManager.getLaunchIntentForPackage(applicationContext.packageName)?.apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        }
        
        val pendingIntent = PendingIntent.getActivity(
            applicationContext, 
            0, 
            intent, 
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val builder = NotificationCompat.Builder(applicationContext, CouveuseServerService.CHANNEL_ID)
            .setContentTitle("Alertes Couveuse")
            .setContentText(texte)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)

        val notification = builder.build()

        val gestionnaire = applicationContext.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        gestionnaire.notify(2, notification)
    }
}

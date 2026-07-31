package com.kissima.couveuse

import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.util.Log
import android.provider.Settings
import com.chaquo.python.PyObject
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform

/**
 * Service d'arrière-plan "invisible" qui maintient le serveur Django local.
 */
class CouveuseServerService : Service() {

    companion object {
        const val CHANNEL_ID = "couveuse_alerts"
    }

    private var demarrageEnCours = false

    override fun onCreate() {
        super.onCreate()
        Log.i("CouveuseService", "Service d'arrière-plan initialisé.")
        lancerServeur()
    }

    private fun lancerServeur() {
        if (demarrageEnCours) return
        demarrageEnCours = true

        Thread {
            try {
                demarrerDjango()
            } catch (e: Exception) {
                Log.e("CouveuseService", "Échec critique démarrage : ${e.message}", e)
            } finally {
                demarrageEnCours = false
            }
        }.start()
    }

    private fun demarrerDjango() {
        try {
            if (!Python.isStarted()) {
                Python.start(AndroidPlatform(applicationContext))
            }
        } catch (e: Exception) {
            Log.w("CouveuseService", "Note: Python engine state: ${e.message}")
        }

        val python = try { Python.getInstance() } catch (e: Exception) { null }
        if (python == null) {
            Log.e("CouveuseService", "Impossible de récupérer l'instance Python.")
            return
        }
        
        val cheminBase = AssetExtractor.extraireSiNecessaire(applicationContext)
        val deviceId = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID) ?: "UNKNOWN_ID"

        Log.i("CouveuseService", "Lancement du serveur invisible (ID: $deviceId)...")
        try {
            val module: PyObject = python.getModule("mobile_entrypoint")
            module.callAttr("demarrer", cheminBase, deviceId)
            Log.i("CouveuseService", "Serveur Django terminé.")
        } catch (e: Exception) {
            Log.e("CouveuseService", "Erreur fatale module python : ${e.message}", e)
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        lancerServeur()
        return START_STICKY
    }

    override fun onDestroy() {
        super.onDestroy()
        Log.i("CouveuseService", "Service arrêté.")
    }
}

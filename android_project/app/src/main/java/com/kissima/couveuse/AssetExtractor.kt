package com.kissima.couveuse

import android.content.Context
import android.util.Log
import java.io.File

/**
 * Chaquopy exécute le code Python directement depuis l'APK (accès fichier
 * limité). Django a besoin d'un vrai répertoire disque pour lire ses
 * templates, ses fichiers static, et écrire sa base SQLite.
 */
object AssetExtractor {

    @Synchronized
    fun extraireSiNecessaire(context: Context): String {
        val destination = File(context.filesDir, "django_app")
        val marqueur = File(destination, ".extrait_ok_v63") // Version 63: Payment Decimal fix & internal client restrictions

        try {
            if (!marqueur.exists()) {
                Log.i("AssetExtractor", "Mise à jour majeure v1.1.2 (v62)...")
                
                // Sauvegarde de la base de données
                val dbFile = File(destination, "couveuse_mobile.sqlite3")
                val tempDb = File(context.cacheDir, "temp_db.sqlite3")
                if (dbFile.exists()) {
                    dbFile.copyTo(tempDb, overwrite = true)
                }

                // Sauvegarde du dossier media (logo, photos)
                val mediaDir = File(destination, "media")
                val tempMedia = File(context.cacheDir, "temp_media")
                if (mediaDir.exists()) {
                    mediaDir.copyRecursively(tempMedia, overwrite = true)
                }

                // Nettoyage complet
                destination.deleteRecursively()
                destination.mkdirs()

                // Extraction des nouveaux fichiers
                copierDossierAssets(context, "django_app", destination)

                // Restauration base de données
                if (tempDb.exists()) {
                    tempDb.copyTo(File(destination, "couveuse_mobile.sqlite3"), overwrite = true)
                    tempDb.delete()
                }

                // Restauration dossier media
                if (tempMedia.exists()) {
                    tempMedia.copyRecursively(File(destination, "media"), overwrite = true)
                    tempMedia.deleteRecursively()
                }

                marqueur.createNewFile()
                Log.i("AssetExtractor", "Mise à jour v62 terminée.")
            }
        } catch (e: Exception) {
            Log.e("AssetExtractor", "Erreur critique extraction : ${e.message}", e)
        }
        return destination.absolutePath
    }

    private fun copierDossierAssets(context: Context, cheminAssets: String, dossierDestination: File) {
        val elements = context.assets.list(cheminAssets) ?: return
        if (elements.isEmpty()) {
            copierFichier(context, cheminAssets, dossierDestination)
            return
        }
        
        dossierDestination.mkdirs()
        for (nom in elements) {
            val cheminEnfant = "$cheminAssets/$nom"
            val destinationEnfant = File(dossierDestination, nom)
            
            val sousElements = context.assets.list(cheminEnfant)
            if (!sousElements.isNullOrEmpty()) {
                copierDossierAssets(context, cheminEnfant, destinationEnfant)
            } else {
                copierFichier(context, cheminEnfant, destinationEnfant)
            }
        }
    }

    private fun copierFichier(context: Context, cheminAssets: String, destination: File) {
        try {
            destination.parentFile?.mkdirs()
            context.assets.open(cheminAssets).use { entree ->
                destination.outputStream().use { sortie -> entree.copyTo(sortie) }
            }
        } catch (e: Exception) {
            Log.w("AssetExtractor", "Note: $cheminAssets non copiable (${e.message})")
        }
    }
}

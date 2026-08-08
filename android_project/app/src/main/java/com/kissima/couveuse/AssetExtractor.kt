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
        val marqueur = File(destination, ".extrait_ok_v60") // Version 60: Release 1.1.2 Final

        try {
            if (!marqueur.exists()) {
                Log.i("AssetExtractor", "Mise à jour majeure v1.1.2 (v60)...")
                
                // Sauvegarde de la base de données
                val dbFile = File(destination, "couveuse_mobile.sqlite3")
                val tempDb = File(context.cacheDir, "temp_db.sqlite3")
                if (dbFile.exists()) {
                    dbFile.copyTo(tempDb, overwrite = true)
                    Log.i("AssetExtractor", "Base de données sauvegardée.")
                }

                // Nettoyage complet pour assurer la mise à jour des templates/logic
                destination.deleteRecursively()
                destination.mkdirs()

                // Extraction des fichiers
                copierDossierAssets(context, "django_app", destination)

                // Restauration de la base de données
                if (tempDb.exists()) {
                    val newDbFile = File(destination, "couveuse_mobile.sqlite3")
                    tempDb.copyTo(newDbFile, overwrite = true)
                    tempDb.delete()
                    Log.i("AssetExtractor", "Base de données restaurée.")
                }

                marqueur.createNewFile()
                Log.i("AssetExtractor", "Mise à jour v60 terminée.")
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

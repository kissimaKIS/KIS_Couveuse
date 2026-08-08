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
        val marqueur = File(destination, ".extrait_ok_v55") // Version 55: v1.1.2 - Client accounts and technical lists

        try {
            if (!marqueur.exists()) {
                Log.i("AssetExtractor", "Mise à jour v1.0.1 (v50)...")
                
                // On préserve la base de données sqlite précieuse
                val dbFile = File(destination, "couveuse_mobile.sqlite3")
                val tempDb = File(context.cacheDir, "temp_db.sqlite3")
                if (dbFile.exists()) {
                    dbFile.copyTo(tempDb, overwrite = true)
                    Log.i("AssetExtractor", "Base de données sauvegardée temporairement.")
                }

                // On nettoie tout le dossier pour installer la nouvelle version proprement
                destination.deleteRecursively()
                destination.mkdirs()

                // On extrait les nouveaux fichiers (Templates, Logic, CSS)
                copierDossierAssets(context, "django_app", destination)

                // On restaure la base de données après nettoyage
                if (tempDb.exists()) {
                    tempDb.copyTo(dbFile, overwrite = true)
                    tempDb.delete()
                    Log.i("AssetExtractor", "Base de données restaurée avec succès.")
                }

                marqueur.createNewFile()
                Log.i("AssetExtractor", "Mise à jour v50 terminée.")
            }
        } catch (e: Exception) {
            Log.e("AssetExtractor", "Erreur critique lors de l'extraction : ${e.message}", e)
        }
        return destination.absolutePath
    }

    private fun copierDossierAssets(context: Context, cheminAssets: String, dossierDestination: File) {
        val elements = context.assets.list(cheminAssets) ?: return
        if (elements.isEmpty()) {
            // C'est un fichier
            copierFichier(context, cheminAssets, dossierDestination)
            return
        }
        
        dossierDestination.mkdirs()
        for (nom in elements) {
            val cheminEnfant = "$cheminAssets/$nom"
            val destinationEnfant = File(dossierDestination, nom)
            
            // On vérifie si c'est un sous-dossier en essayant de lister son contenu
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
            // Parfois list() renvoie des dossiers vides comme des fichiers, on ignore l'erreur
            Log.w("AssetExtractor", "Note: $cheminAssets n'est pas un fichier copiable (${e.message})")
        }
    }
}

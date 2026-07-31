package com.kissima.couveuse

import android.content.Context
import android.util.Log
import java.io.File

/**
 * Chaquopy exécute le code Python directement depuis l'APK (accès fichier
 * limité). Django a besoin d'un vrai répertoire disque pour lire ses
 * templates, ses fichiers static, et écrire sa base SQLite. Cette classe
 * copie donc une seule fois (au premier lancement) le contenu de
 * assets/django_app/ vers le stockage interne de l'application
 * (context.filesDir), où Django peut ensuite lire/écrire normalement.
 */
object AssetExtractor {

    @Synchronized
    fun extraireSiNecessaire(context: Context): String {
        val destination = File(context.filesDir, "django_app")
        val marqueur = File(destination, ".extrait_ok_v45") // Version 45: Fixed Espece (Species) form logic

        try {
            if (!marqueur.exists()) {
                Log.i("AssetExtractor", "Extraction des assets vers ${destination.absolutePath}...")
                // On ne supprime pas tout pour garder la base de données
                // Mais on va écraser templates, static et media
                val tpl = File(destination, "templates")
                val stc = File(destination, "static")
                val med = File(destination, "media")
                
                tpl.deleteRecursively()
                stc.deleteRecursively()
                med.deleteRecursively()
                
                destination.mkdirs()
                copierDossierAssets(context, "django_app", destination)
                marqueur.createNewFile()
                Log.i("AssetExtractor", "Extraction terminée.")
            }
        } catch (e: Exception) {
            Log.e("AssetExtractor", "Erreur critique lors de l'extraction : ${e.message}", e)
        }
        return destination.absolutePath
    }

    private fun copierDossierAssets(context: Context, cheminAssets: String, dossierDestination: File) {
        val elements = context.assets.list(cheminAssets) ?: return
        if (elements.isEmpty()) {
            // Fichier (pas un dossier) : on le copie directement.
            copierFichier(context, cheminAssets, File(dossierDestination.parentFile, File(cheminAssets).name))
            return
        }
        dossierDestination.mkdirs()
        for (nom in elements) {
            val cheminEnfant = "$cheminAssets/$nom"
            val sousElements = context.assets.list(cheminEnfant)
            if (!sousElements.isNullOrEmpty()) {
                copierDossierAssets(context, cheminEnfant, File(dossierDestination, nom))
            } else {
                copierFichier(context, cheminEnfant, File(dossierDestination, nom))
            }
        }
    }

    private fun copierFichier(context: Context, cheminAssets: String, destination: File) {
        destination.parentFile?.mkdirs()
        context.assets.open(cheminAssets).use { entree ->
            destination.outputStream().use { sortie -> entree.copyTo(sortie) }
        }
    }
}

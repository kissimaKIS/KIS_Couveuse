package com.kissima.couveuse

import android.app.Activity
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.print.PrintAttributes
import android.print.PrintManager
import android.util.Log
import android.view.View
import android.webkit.CookieManager
import android.webkit.JavascriptInterface
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.FileProvider
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var loadingLayout: LinearLayout
    private lateinit var statusText: TextView
    private val urlServeur = "http://127.0.0.1:8080"
    private val handler = Handler(Looper.getMainLooper())

    private var filePathCallback: ValueCallback<Array<Uri>>? = null
    private val filePickerLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            val results = WebChromeClient.FileChooserParams.parseResult(result.resultCode, result.data)
            filePathCallback?.onReceiveValue(results)
        } else {
            filePathCallback?.onReceiveValue(null)
        }
        filePathCallback = null
    }

    @android.annotation.SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Création du canal de notification pour les alertes
        creerCanalNotification()

        // Démarre le serveur Django embarqué (mode invisible)
        startService(Intent(this, CouveuseServerService::class.java))

        setContentView(R.layout.activity_main)
        
        val mainRoot = findViewById<View>(R.id.mainRoot)
        ViewCompat.setOnApplyWindowInsetsListener(mainRoot) { v, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom)
            insets
        }

        webView = findViewById(R.id.webView)
        loadingLayout = findViewById(R.id.loadingLayout)
        statusText = findViewById(R.id.statusText)

        // Demande la permission de notification
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            requestPermissions(arrayOf(android.Manifest.permission.POST_NOTIFICATIONS), 101)
        }

        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            databaseEnabled = true
            cacheMode = android.webkit.WebSettings.LOAD_DEFAULT
        }
        
        webView.addJavascriptInterface(WebAppInterface(), "CouveuseApp")
        
        webView.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView?, url: String?) {
                super.onPageFinished(view, url)
                if (url != null && url.contains("8080")) {
                    loadingLayout.visibility = View.GONE
                    webView.visibility = View.VISIBLE
                }
            }

            override fun shouldOverrideUrlLoading(view: WebView?, url: String?): Boolean {
                if (url == null) return false
                
                if (url.startsWith("whatsapp:") || url.contains("wa.me") || url.startsWith("tel:") || url.startsWith("mailto:")) {
                    try {
                        val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                        startActivity(intent)
                        return true
                    } catch (e: Exception) {
                        Toast.makeText(this@MainActivity, "Impossible d'ouvrir l'application demandée", Toast.LENGTH_SHORT).show()
                        return true
                    }
                }
                return false
            }
        }
        
        webView.setDownloadListener { url, _, contentDisposition, _, _ ->
            Toast.makeText(this, "Préparation du fichier...", Toast.LENGTH_SHORT).show()
            telechargerEtPartagerFichier(url, contentDisposition)
        }
        
        webView.webChromeClient = object : WebChromeClient() {
            override fun onShowFileChooser(
                webView: WebView?,
                callback: ValueCallback<Array<Uri>>?,
                params: FileChooserParams?
            ): Boolean {
                filePathCallback?.onReceiveValue(null)
                filePathCallback = callback
                val intent = params?.createIntent()
                try {
                    filePickerLauncher.launch(intent)
                } catch (e: Exception) {
                    filePathCallback = null
                    return false
                }
                return true
            }
        }

        attendreServeurPuisCharger(0)
    }

    private fun creerCanalNotification() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CouveuseServerService.CHANNEL_ID,
                "Alertes Couveuse",
                NotificationManager.IMPORTANCE_HIGH
            ).apply { description = "Notifications de mirage et éclosion" }
            val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            manager.createNotificationChannel(channel)
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        // Si l'activité est déjà ouverte, on recharge l'URL de base si besoin
        if (serveurRepond()) {
            webView.loadUrl(urlServeur)
        }
    }

    private fun attendreServeurPuisCharger(tentative: Int) {
        Thread {
            val disponible = serveurRepond()
            handler.post {
                if (disponible) {
                    webView.loadUrl(urlServeur)
                } else if (tentative < 120) {
                    statusText.text = "Initialisation du serveur... ($tentative)"
                    handler.postDelayed({ attendreServeurPuisCharger(tentative + 1) }, 500)
                } else {
                    loadingLayout.visibility = View.GONE
                    webView.visibility = View.VISIBLE
                    webView.loadData(
                        "<html><body style='text-align:center;padding:50px;'><h3>Erreur de démarrage</h3><p>Le serveur n'a pas pu s'allumer.</p></body></html>",
                        "text/html", "utf-8"
                    )
                }
            }
        }.start()
    }

    private fun serveurRepond(): Boolean {
        return try {
            val connexion = URL(urlServeur).openConnection() as HttpURLConnection
            connexion.connectTimeout = 500
            connexion.requestMethod = "GET"
            val code = connexion.responseCode
            connexion.disconnect()
            (code in 200..499)
        } catch (_: IOException) {
            false
        }
    }

    inner class WebAppInterface {
        @JavascriptInterface
        fun imprimerPage() {
            handler.post {
                try {
                    val printManager = getSystemService(Context.PRINT_SERVICE) as PrintManager
                    val jobName = "${getString(R.string.app_name)} Document"
                    val printAdapter = webView.createPrintDocumentAdapter(jobName)
                    printManager.print(jobName, printAdapter, PrintAttributes.Builder().build())
                } catch (e: Exception) {
                    Log.e("MainActivity", "Erreur Impression", e)
                }
            }
        }
    }

    private fun telechargerEtPartagerFichier(url: String, contentDisposition: String) {
        val fileName = contentDisposition.split("filename=").lastOrNull()?.replace("\"", "") ?: "sauvegarde.sqlite3"
        val cookies = CookieManager.getInstance().getCookie(url)
        val extension = if (fileName.contains(".")) fileName.split(".").last() else "sqlite3"
        val mimeType = when(extension) {
            "pdf" -> "application/pdf"
            "sqlite3" -> "application/x-sqlite3"
            else -> "application/octet-stream"
        }

        Thread {
            try {
                val connection = URL(url).openConnection() as HttpURLConnection
                connection.requestMethod = "GET"
                if (!cookies.isNullOrEmpty()) connection.setRequestProperty("Cookie", cookies)
                connection.connect()

                if (connection.responseCode == HttpURLConnection.HTTP_OK) {
                    val folder = File(externalCacheDir, "exports")
                    if (!folder.exists()) folder.mkdirs()
                    
                    val file = File(folder, fileName)
                    val outputStream = FileOutputStream(file)
                    connection.inputStream.use { input -> input.copyTo(outputStream) }
                    outputStream.close()

                    handler.post { partagerFichier(file, mimeType) }
                }
            } catch (e: Exception) {
                Log.e("MainActivity", "Erreur Téléchargement", e)
            }
        }.start()
    }

    private fun partagerFichier(file: File, mimeType: String) {
        try {
            val authority = "com.kissima.couveuse.fileprovider"
            val uri = FileProvider.getUriForFile(this, authority, file)
            
            val intent = if (mimeType.contains("pdf")) {
                Intent(Intent.ACTION_VIEW).apply {
                    setDataAndType(uri, mimeType)
                    addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                }
            } else {
                Intent(Intent.ACTION_SEND).apply {
                    type = mimeType
                    putExtra(Intent.EXTRA_STREAM, uri)
                    addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                }
            }
            startActivity(Intent.createChooser(intent, "Partager le fichier"))
        } catch (e: Exception) {
            Log.e("MainActivity", "Erreur Partage", e)
            Toast.makeText(this, "Erreur lors du partage", Toast.LENGTH_SHORT).show()
        }
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        val currentUrl = webView.url ?: ""
        val uri = Uri.parse(currentUrl)
        val path = uri.path ?: ""
        
        if (path == "/" || path == "/dashboard/" || path == "" || !webView.canGoBack()) {
            super.onBackPressed()
            finish()
        } else {
            webView.goBack()
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        stopService(Intent(this, CouveuseServerService::class.java))
    }
}

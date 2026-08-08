package com.kissima.couveuse

import android.app.Activity
import android.app.NotificationChannel
import android.app.NotificationManager
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
    private var serveurPret = false

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

        // Initialisation canal notification
        creerCanalNotification()

        // Lancement serveur invisible
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

        // Permission notification
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
                        Toast.makeText(this@MainActivity, "Application non installée", Toast.LENGTH_SHORT).show()
                        return true
                    }
                }
                return false
            }
        }
        
        webView.setDownloadListener { url, _, contentDisposition, _, _ ->
            telechargerEtPartagerFichier(url, contentDisposition)
        }
        
        webView.webChromeClient = object : WebChromeClient() {
            override fun onShowFileChooser(webView: WebView?, callback: ValueCallback<Array<Uri>>?, params: FileChooserParams?): Boolean {
                filePathCallback?.onReceiveValue(null)
                filePathCallback = callback
                try { filePickerLauncher.launch(params?.createIntent()) } catch (e: Exception) { filePathCallback = null; return false }
                return true
            }
        }

        attendreServeurPuisCharger(0)
    }

    private fun creerCanalNotification() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val name = "Alertes Couveuse"
            val channel = NotificationChannel(CouveuseServerService.CHANNEL_ID, name, NotificationManager.IMPORTANCE_HIGH)
            val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            manager.createNotificationChannel(channel)
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        if (serveurPret) webView.loadUrl(urlServeur)
    }

    private fun attendreServeurPuisCharger(tentative: Int) {
        Thread {
            val disponible = serveurRepond()
            handler.post {
                if (disponible) {
                    serveurPret = true
                    webView.loadUrl(urlServeur)
                } else if (tentative < 150) {
                    statusText.text = "Démarrage du système... ($tentative)"
                    handler.postDelayed({ attendreServeurPuisCharger(tentative + 1) }, 600)
                } else {
                    loadingLayout.visibility = View.GONE
                    webView.visibility = View.VISIBLE
                    webView.loadData("<html><body style='text-align:center;padding:50px;'><h3>Erreur de démarrage</h3><p>Veuillez relancer l'application.</p></body></html>", "text/html", "utf-8")
                }
            }
        }.start()
    }

    private fun serveurRepond(): Boolean {
        return try {
            val connexion = URL(urlServeur).openConnection() as HttpURLConnection
            connexion.connectTimeout = 600
            connexion.requestMethod = "GET"
            val code = connexion.responseCode
            connexion.disconnect()
            (code in 200..499)
        } catch (_: IOException) { false }
    }

    inner class WebAppInterface {
        @JavascriptInterface
        fun imprimerPage() {
            handler.post {
                try {
                    val printManager = getSystemService(Context.PRINT_SERVICE) as PrintManager
                    val printAdapter = webView.createPrintDocumentAdapter("Document KIS")
                    printManager.print("Imprimer", printAdapter, PrintAttributes.Builder().build())
                } catch (e: Exception) { Log.e("MainActivity", "Erreur Impression", e) }
            }
        }
    }

    private fun telechargerEtPartagerFichier(url: String, contentDisposition: String) {
        val fileName = contentDisposition.split("filename=").lastOrNull()?.replace("\"", "") ?: "sauvegarde.sqlite3"
        val cookies = CookieManager.getInstance().getCookie(url)
        Thread {
            try {
                val connection = URL(url).openConnection() as HttpURLConnection
                if (!cookies.isNullOrEmpty()) connection.setRequestProperty("Cookie", cookies)
                connection.connect()
                if (connection.responseCode == HttpURLConnection.HTTP_OK) {
                    val folder = File(externalCacheDir, "exports").apply { if (!exists()) mkdirs() }
                    val file = File(folder, fileName)
                    FileOutputStream(file).use { connection.inputStream.copyTo(it) }
                    handler.post { partagerFichier(file) }
                }
            } catch (e: Exception) { Log.e("MainActivity", "Erreur Téléchargement", e) }
        }.start()
    }

    private fun partagerFichier(file: File) {
        try {
            val uri = FileProvider.getUriForFile(this, "com.kissima.couveuse.fileprovider", file)
            val intent = Intent(Intent.ACTION_SEND).apply {
                type = if (file.name.endsWith(".pdf")) "application/pdf" else "application/octet-stream"
                putExtra(Intent.EXTRA_STREAM, uri)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            startActivity(Intent.createChooser(intent, "Partager le fichier"))
        } catch (e: Exception) { Log.e("MainActivity", "Erreur Partage", e) }
    }

    override fun onBackPressed() {
        val path = Uri.parse(webView.url ?: "").path ?: ""
        if (path == "/" || path == "/dashboard/" || path == "" || !webView.canGoBack()) {
            super.onBackPressed()
            finish()
        } else { webView.goBack() }
    }

    override fun onDestroy() {
        super.onDestroy()
        stopService(Intent(this, CouveuseServerService::class.java))
    }
}

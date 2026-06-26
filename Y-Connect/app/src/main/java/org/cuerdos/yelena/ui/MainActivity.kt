package org.cuerdos.yelena.ui

import android.content.ClipboardManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.provider.Settings
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.net.Uri
import android.text.format.Formatter
import androidx.core.app.NotificationCompat
import androidx.core.content.FileProvider
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.app.AppCompatDelegate
import androidx.core.view.WindowCompat
import androidx.lifecycle.lifecycleScope
import androidx.navigation.fragment.NavHostFragment
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import org.cuerdos.yelena.R
import org.cuerdos.yelena.YelenaNotificationListener
import org.cuerdos.yelena.YelenaService
import org.cuerdos.yelena.databinding.ActivityMainBinding
import org.cuerdos.yelena.websocket.YelenaWebSocket

class MainActivity : AppCompatActivity() {

    companion object {
        private const val FILE_CHANNEL_ID = "yelena_files"
        private var FILE_NOTIF_ID = 2000
    }

    private lateinit var binding: ActivityMainBinding
    private var clipboardListener: ClipboardManager.OnPrimaryClipChangedListener? = null
    private var fileOfferDialog: AlertDialog? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        val prefs = getSharedPreferences("yelena_prefs", Context.MODE_PRIVATE)
        AppCompatDelegate.setDefaultNightMode(
            prefs.getInt("theme_mode", AppCompatDelegate.MODE_NIGHT_FOLLOW_SYSTEM)
        )
        val overlayRes = accentOverlay(prefs.getString("accent_color", "#5a7a22") ?: "#5a7a22")
        if (overlayRes != 0) theme.applyStyle(overlayRes, true)

        super.onCreate(savedInstanceState)

        WindowCompat.setDecorFitsSystemWindows(window, true)
        window.statusBarColor     = Color.TRANSPARENT
        window.navigationBarColor = Color.TRANSPARENT

        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        YelenaWebSocket.appContext = applicationContext

        if (!isNotificationListenerEnabled()) {
            AlertDialog.Builder(this)
                .setTitle(getString(R.string.notif_permission_title))
                .setMessage(getString(R.string.notif_permission_message))
                .setPositiveButton(getString(R.string.notif_permission_open)) { _, _ ->
                    startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
                }
                .setNegativeButton(getString(R.string.notif_permission_skip), null)
                .show()
        }

        val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboardListener = ClipboardManager.OnPrimaryClipChangedListener {
            if (YelenaWebSocket.shouldIgnoreNextClipChange()) return@OnPrimaryClipChangedListener
            val text = cm.primaryClip?.getItemAt(0)
                ?.coerceToText(applicationContext)?.toString()
            if (!text.isNullOrEmpty() && text != YelenaWebSocket.clipboard.value) {
                YelenaWebSocket.sendClipboard(text)
            }
        }
        cm.addPrimaryClipChangedListener(clipboardListener!!)

        lifecycleScope.launch {
            YelenaWebSocket.fileOffer.collectLatest { offer ->
                if (offer != null) showFileOfferDialog(offer)
                else { fileOfferDialog?.dismiss(); fileOfferDialog = null }
            }
        }

        lifecycleScope.launch {
            YelenaWebSocket.fileReceived.collectLatest { received ->
                if (received != null) {
                    showFileReceivedNotification(received.first, received.second)
                    YelenaWebSocket.fileReceived.value = null
                }
            }
        }

        createFileNotificationChannel()

        val ip   = prefs.getString("last_ip", null)
        val port = prefs.getInt("last_port", YelenaWebSocket.WS_PORT)

        if (!ip.isNullOrEmpty()) {
            if (!YelenaWebSocket.isConnectedOrConnecting()) {
                YelenaWebSocket.connect(ip, port)
            }
            if (savedInstanceState == null) {
                val navHost = supportFragmentManager
                    .findFragmentById(R.id.nav_host) as NavHostFragment
                val graph = navHost.navController.navInflater.inflate(R.navigation.nav_graph)
                graph.setStartDestination(R.id.mainFragment)
                navHost.navController.setGraph(graph, null)
            }
        }
    }

    private fun showFileOfferDialog(offer: Map<String, String>) {
        fileOfferDialog?.dismiss()
        val tid  = offer["transfer_id"]?.takeIf { it.isNotEmpty() } ?: return
        val name = offer["name"] ?: "?"
        val size = offer["size"]?.toLongOrNull() ?: 0L
        val ext  = offer["ext"] ?: "?"
        val sizeStr = Formatter.formatShortFileSize(this, size)
        fileOfferDialog = AlertDialog.Builder(this)
            .setTitle(getString(R.string.file_incoming_title))
            .setMessage(getString(R.string.file_incoming_message, name, ext, sizeStr))
            .setPositiveButton(getString(R.string.file_accept)) { _, _ ->
                YelenaWebSocket.sendFileAccept(tid)
            }
            .setNegativeButton(getString(R.string.file_reject)) { _, _ ->
                YelenaWebSocket.sendFileReject(tid)
                YelenaWebSocket.fileOffer.value = null
            }
            .setCancelable(false)
            .show()
    }

    private fun createFileNotificationChannel() {
        val ch = NotificationChannel(
            FILE_CHANNEL_ID,
            getString(R.string.file_notif_channel_name),
            NotificationManager.IMPORTANCE_DEFAULT
        ).apply { setShowBadge(true) }
        getSystemService(NotificationManager::class.java).createNotificationChannel(ch)
    }

    private fun showFileReceivedNotification(name: String, path: String) {
        val uri = try {
            androidx.core.content.FileProvider.getUriForFile(
                this,
                "$packageName.provider",
                java.io.File(path)
            )
        } catch (_: Exception) {
            android.net.Uri.parse("content://downloads/my_downloads")
        }
        val openIntent = PendingIntent.getActivity(
            this, System.currentTimeMillis().toInt(),
            Intent(Intent.ACTION_VIEW).apply {
                setDataAndType(uri, contentResolver.getType(uri) ?: "*/*")
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            },
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )
        val notif = NotificationCompat.Builder(this, FILE_CHANNEL_ID)
            .setSmallIcon(android.R.drawable.stat_sys_download_done)
            .setContentTitle(getString(R.string.file_received_title))
            .setContentText(name)
            .setContentIntent(openIntent)
            .setAutoCancel(true)
            .build()
        getSystemService(NotificationManager::class.java)
            .notify(FILE_NOTIF_ID++, notif)
    }

    private fun accentOverlay(hex: String): Int = when (hex.lowercase()) {
        "#5a7a22" -> R.style.ThemeOverlay_Yelena_Green
        "#9b59b6" -> R.style.ThemeOverlay_Yelena_Purple
        "#e74c3c" -> R.style.ThemeOverlay_Yelena_Red
        "#f39c12" -> R.style.ThemeOverlay_Yelena_Yellow
        "#2980b9" -> R.style.ThemeOverlay_Yelena_Blue
        "#16a085" -> R.style.ThemeOverlay_Yelena_Teal
        "#e91e63" -> R.style.ThemeOverlay_Yelena_Pink
        "#e67e22" -> R.style.ThemeOverlay_Yelena_Orange
        else      -> 0
    }

    private fun isNotificationListenerEnabled(): Boolean {
        val cn   = ComponentName(this, YelenaNotificationListener::class.java)
        val flat = Settings.Secure.getString(contentResolver, "enabled_notification_listeners")
        return flat != null && flat.contains(cn.flattenToString())
    }

    override fun onStart() {
        super.onStart()
        val prefs = getSharedPreferences("yelena_prefs", Context.MODE_PRIVATE)
        if (!prefs.getString("last_ip", null).isNullOrEmpty()) {
            YelenaService.start(this)
        }
    }

    fun applyAccentColor(hex: String) {
        try {
            val prefs = getSharedPreferences("yelena_prefs", Context.MODE_PRIVATE)
            prefs.edit().putString("accent_color", hex).apply()
            recreate()
        } catch (_: Exception) {}
    }

    override fun onDestroy() {
        super.onDestroy()
        val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboardListener?.let { cm.removePrimaryClipChangedListener(it) }
        fileOfferDialog?.dismiss()
    }
}
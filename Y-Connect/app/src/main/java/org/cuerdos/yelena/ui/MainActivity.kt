package org.cuerdos.yelena.ui

import android.content.ClipboardManager
import android.content.Context
import android.content.ComponentName
import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.provider.Settings
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.app.AppCompatDelegate
import androidx.core.view.WindowCompat
import androidx.navigation.fragment.NavHostFragment
import org.cuerdos.yelena.R
import org.cuerdos.yelena.YelenaNotificationListener
import org.cuerdos.yelena.YelenaService
import org.cuerdos.yelena.databinding.ActivityMainBinding
import org.cuerdos.yelena.websocket.YelenaWebSocket

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private var clipboardListener: ClipboardManager.OnPrimaryClipChangedListener? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        val prefs = getSharedPreferences("yelena_prefs", Context.MODE_PRIVATE)
        AppCompatDelegate.setDefaultNightMode(
            prefs.getInt("theme_mode", AppCompatDelegate.MODE_NIGHT_FOLLOW_SYSTEM)
        )

        val overlayRes = accentOverlay(prefs.getString("accent_color", "#5a7a22") ?: "#5a7a22")
        if (overlayRes != 0) theme.applyStyle(overlayRes, true)

        super.onCreate(savedInstanceState)

        WindowCompat.setDecorFitsSystemWindows(window, false)
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
    }
}
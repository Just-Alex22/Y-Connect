package org.cuerdos.yelena.ui

import android.content.ClipboardManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.res.ColorStateList
import android.graphics.Color
import android.os.Bundle
import android.provider.Settings
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.app.AppCompatDelegate
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
        super.onCreate(savedInstanceState)

        val prefs = getSharedPreferences("yelena_prefs", Context.MODE_PRIVATE)
        AppCompatDelegate.setDefaultNightMode(
            prefs.getInt("theme_mode", AppCompatDelegate.MODE_NIGHT_FOLLOW_SYSTEM)
        )

        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        YelenaWebSocket.appContext = applicationContext

        // Portapapeles Android → PC
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

        val ip   = prefs.getString("last_ip", null)
        val port = prefs.getInt("last_port", YelenaWebSocket.WS_PORT)

        if (!ip.isNullOrEmpty()) {
            // Ya se conectó antes → reconectar y saltar directo al main
            if (!YelenaWebSocket.isConnectedOrConnecting()) {
                YelenaWebSocket.connect(ip, port)
            }
            // Cambiar startDestination a mainFragment en tiempo de ejecución
            if (savedInstanceState == null) {
                val navHost = supportFragmentManager
                    .findFragmentById(R.id.nav_host) as NavHostFragment
                val graph = navHost.navController.navInflater.inflate(R.navigation.nav_graph)
                graph.setStartDestination(R.id.mainFragment)
                navHost.navController.setGraph(graph, null)
            }
        }
    }

    override fun onStart() {
        super.onStart()
        val prefs = getSharedPreferences("yelena_prefs", Context.MODE_PRIVATE)
        if (!prefs.getString("last_ip", null).isNullOrEmpty()) {
            YelenaService.start(this)
        }
    }

    private fun isNotificationListenerEnabled(): Boolean {
        val cn = ComponentName(this, YelenaNotificationListener::class.java)
        val flat = Settings.Secure.getString(contentResolver, "enabled_notification_listeners")
        return flat != null && flat.contains(cn.flattenToString())
    }

    fun applyAccentColor(hex: String) {
        // Guardar y aplicar el color de acento en runtime
        // Los botones y switches se actualizan via recreate
        try {
            val color = Color.parseColor(hex)
            // Actualizar el tema en runtime requiere recrear la activity
            recreate()
        } catch (_: Exception) {}
    }

    override fun onDestroy() {
        super.onDestroy()
        val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboardListener?.let { cm.removePrimaryClipChangedListener(it) }
    }
}
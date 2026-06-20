package org.cuerdos.yelena.ui.main

import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.graphics.Bitmap
import android.media.MediaMetadata
import android.media.session.MediaSessionManager
import android.media.session.PlaybackState
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.BatteryManager
import android.os.Build
import android.os.Bundle
import android.util.Base64
import android.view.*
import androidx.core.view.GravityCompat
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import androidx.navigation.fragment.findNavController
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import org.cuerdos.yelena.R
import org.cuerdos.yelena.databinding.FragmentMainBinding
import org.cuerdos.yelena.model.*
import org.cuerdos.yelena.websocket.ConnectionState
import org.cuerdos.yelena.websocket.YelenaWebSocket
import java.io.ByteArrayOutputStream

class MainFragment : Fragment() {
    private var _binding: FragmentMainBinding? = null
    private val binding get() = _binding!!

    override fun onCreateView(i: LayoutInflater, c: ViewGroup?, s: Bundle?): View {
        _binding = FragmentMainBinding.inflate(i, c, false)
        return binding.root
    }

    override fun onViewCreated(view: View, s: Bundle?) {
        super.onViewCreated(view, s)
        binding.root.alpha = 0f
        binding.root.animate().alpha(1f).setDuration(400).start()
        setupDrawer()
        setupMediaControls()
        binding.cardTerminal.setOnClickListener {
            findNavController().navigate(R.id.action_main_to_terminal)
        }
        binding.cardTrackpad.setOnClickListener {
            findNavController().navigate(R.id.action_main_to_trackpad)
        }
        observeState()
    }

    private fun setupDrawer() {
        binding.btnMenu.setOnClickListener {
            binding.drawerLayout.openDrawer(GravityCompat.START)
        }
        binding.navView.setNavigationItemSelectedListener { item ->
            binding.drawerLayout.closeDrawers()
            when (item.itemId) {
                R.id.nav_trackpad      -> { findNavController().navigate(R.id.action_main_to_trackpad);      true }
                R.id.nav_terminal      -> { findNavController().navigate(R.id.action_main_to_terminal);      true }
                R.id.nav_notifications -> { findNavController().navigate(R.id.action_main_to_notifications); true }
                R.id.nav_processes     -> { findNavController().navigate(R.id.action_main_to_processes);     true }
                R.id.nav_apps          -> { findNavController().navigate(R.id.action_main_to_apps);          true }
                R.id.nav_clipboard     -> { findNavController().navigate(R.id.action_main_to_clipboard);     true }
                R.id.nav_settings      -> { findNavController().navigate(R.id.action_main_to_settings);      true }
                R.id.nav_about         -> { findNavController().navigate(R.id.action_main_to_about);         true }
                R.id.nav_disconnect    -> {
                    val prefs = requireContext()
                        .getSharedPreferences("yelena_prefs", android.content.Context.MODE_PRIVATE)
                    prefs.edit().remove("last_ip").remove("last_port").apply()
                    YelenaWebSocket.disconnect()
                    findNavController().navigate(R.id.action_main_to_connect)
                    true
                }
                else -> false
            }
        }
    }

    private fun setupMediaControls() {
        binding.btnPrev.setOnClickListener     { YelenaWebSocket.sendMediaCommand("prev") }
        binding.btnPlayPause.setOnClickListener { YelenaWebSocket.sendMediaCommand("play_pause") }
        binding.btnNext.setOnClickListener      { YelenaWebSocket.sendMediaCommand("next") }
        binding.btnVolDown.setOnClickListener   { YelenaWebSocket.sendMediaCommand("vol_down") }
        binding.btnVolUp.setOnClickListener     { YelenaWebSocket.sendMediaCommand("vol_up") }
    }

    private fun observeState() {
        viewLifecycleOwner.lifecycleScope.launch {
            YelenaWebSocket.connectionState.collectLatest { state ->
                when (state) {
                    is ConnectionState.Connected -> {
                        binding.tvConnectionStatus.text =
                            getString(R.string.connected_to, state.pcInfo.hostname)
                        binding.tvConnectionStatus.setTextColor(
                            requireContext().getColor(R.color.accent_green))
                        binding.connectionDot.setBackgroundResource(R.drawable.shape_dot_green)
                    }
                    is ConnectionState.Connecting -> {
                        binding.tvConnectionStatus.setText(R.string.connecting)
                        binding.tvConnectionStatus.setTextColor(
                            requireContext().getColor(R.color.text_secondary))
                        binding.connectionDot.setBackgroundResource(R.drawable.shape_dot)
                    }
                    is ConnectionState.Disconnected -> {
                        binding.tvConnectionStatus.setText(R.string.disconnected)
                        binding.tvConnectionStatus.setTextColor(
                            requireContext().getColor(R.color.text_disabled))
                        binding.connectionDot.setBackgroundResource(R.drawable.shape_dot)
                    }
                    is ConnectionState.Error -> {
                        binding.tvConnectionStatus.text =
                            getString(R.string.error_prefix, state.message)
                        binding.tvConnectionStatus.setTextColor(
                            requireContext().getColor(R.color.accent_red))
                        binding.connectionDot.setBackgroundResource(R.drawable.shape_dot)
                    }
                }
            }
        }
        viewLifecycleOwner.lifecycleScope.launch {
            YelenaWebSocket.pcResources.collectLatest { updateResources(it) }
        }
        viewLifecycleOwner.lifecycleScope.launch {
            YelenaWebSocket.pcMedia.collectLatest { updateMedia(it) }
        }

        viewLifecycleOwner.lifecycleScope.launch {
            while (true) {
                sendWifiSignal()
                sendBattery()
                sendPhoneMedia()
                delay(5_000)
            }
        }
    }

    private fun sendPhoneMedia() {
        try {
            val msm = requireContext().getSystemService(Context.MEDIA_SESSION_SERVICE) as MediaSessionManager
            val cn = android.content.ComponentName(requireContext(), org.cuerdos.yelena.YelenaNotificationListener::class.java)
            val controllers = msm.getActiveSessions(cn)
            val ctrl = controllers.firstOrNull() ?: return
            val meta  = ctrl.metadata
            val state = ctrl.playbackState
            val title   = meta?.getString(MediaMetadata.METADATA_KEY_TITLE) ?: ""
            val artist  = meta?.getString(MediaMetadata.METADATA_KEY_ARTIST) ?: ""
            val playing = state?.state == PlaybackState.STATE_PLAYING
            val artworkBase64 = meta?.getBitmap(MediaMetadata.METADATA_KEY_ALBUM_ART)
                ?: meta?.getBitmap(MediaMetadata.METADATA_KEY_ART)
            val artwork = artworkBase64?.let { bmp ->
                val scaled = Bitmap.createScaledBitmap(bmp, 200, 200, true)
                val out = ByteArrayOutputStream()
                scaled.compress(Bitmap.CompressFormat.JPEG, 75, out)
                Base64.encodeToString(out.toByteArray(), Base64.NO_WRAP)
            }
            YelenaWebSocket.sendPhoneMedia(title, artist, playing, artwork)
        } catch (_: Exception) {}
    }

    private fun sendBattery() {
        try {
            val intent = requireContext().registerReceiver(
                null, IntentFilter(Intent.ACTION_BATTERY_CHANGED)
            ) ?: return
            val level = intent.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
            val scale = intent.getIntExtra(BatteryManager.EXTRA_SCALE, -1)
            if (level < 0 || scale <= 0) return
            val pct = (level * 100 / scale)
            val status = intent.getIntExtra(BatteryManager.EXTRA_STATUS, -1)
            val charging = status == BatteryManager.BATTERY_STATUS_CHARGING
                        || status == BatteryManager.BATTERY_STATUS_FULL
            YelenaWebSocket.sendBattery(pct, charging)
        } catch (_: Exception) {}
    }

    private fun sendWifiSignal() {
        try {
            val cm = requireContext().applicationContext
                .getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
            val rssi: Int
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val network = cm.activeNetwork ?: return
                val caps = cm.getNetworkCapabilities(network) ?: return
                if (!caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)) return
                val signalStrength = caps.signalStrength
                if (signalStrength == NetworkCapabilities.SIGNAL_STRENGTH_UNSPECIFIED) return
                rssi = signalStrength
            } else {
                @Suppress("DEPRECATION")
                val wm = requireContext().applicationContext
                    .getSystemService(Context.WIFI_SERVICE) as android.net.wifi.WifiManager
                @Suppress("DEPRECATION")
                val info = wm.connectionInfo ?: return
                @Suppress("DEPRECATION")
                rssi = info.rssi
            }
            if (rssi != 0 && rssi > -120) {
                YelenaWebSocket.sendWifiSignal(rssi)
            }
        } catch (_: Exception) {}
    }

    private fun updateResources(res: PcResources) {
        binding.rowCpu.tvResLabel.text       = getString(R.string.cpu_label)
        binding.rowCpu.tvResValue.text       = "${res.cpuPercent.toInt()}%"
        binding.rowCpu.progressRes.progress  = res.cpuPercent.toInt()
        binding.rowRam.tvResLabel.text       = getString(R.string.ram_label)
        binding.rowRam.tvResValue.text       = "${"%.1f".format(res.ramUsedGb)}/${"%.1f".format(res.ramTotalGb)} GB"
        binding.rowRam.progressRes.progress  = res.ramPercent.toInt()
        binding.rowDisk.tvResLabel.text      = getString(R.string.disk_label)
        binding.rowDisk.tvResValue.text      = "${"%.1f".format(res.diskUsedGb)}/${"%.1f".format(res.diskTotalGb)} GB"
        binding.rowDisk.progressRes.progress = res.diskPercent.toInt()
        val h = res.uptimeSeconds / 3600
        val m = (res.uptimeSeconds % 3600) / 60
        binding.tvUptime.text = "${h}h ${m}m"
    }

    private fun updateMedia(media: PcMedia) {
        if (media.title.isNotBlank()) {
            binding.tvMediaTitle.text       = media.title
            binding.tvMediaTitle.visibility = View.VISIBLE
        } else {
            binding.tvMediaTitle.visibility = View.GONE
        }
        if (media.artist.isNotBlank()) {
            binding.tvMediaArtist.text       = media.artist
            binding.tvMediaArtist.visibility = View.VISIBLE
        } else {
            binding.tvMediaArtist.visibility = View.GONE
        }
        binding.btnPlayPause.setImageResource(
            if (media.playing) R.drawable.ic_pause else R.drawable.ic_play
        )
    }

    override fun onDestroyView() { super.onDestroyView(); _binding = null }
}
package org.cuerdos.yelena.websocket

import android.content.ClipData
import android.content.ClipboardManager
import android.content.ContentValues
import android.content.Context
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import android.util.Base64
import android.util.Log
import io.ktor.client.*
import io.ktor.client.engine.cio.*
import io.ktor.client.plugins.websocket.*
import io.ktor.websocket.*
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import org.cuerdos.yelena.model.*
import java.io.File

sealed class ConnectionState {
    object Disconnected : ConnectionState()
    object Connecting   : ConnectionState()
    data class Connected(val pcInfo: PcInfo) : ConnectionState()
    data class Error(val message: String)    : ConnectionState()
}

object YelenaWebSocket {

    const val WS_PORT = 8765
    private const val TAG = "YelenaWS"

    private val json   = Json { ignoreUnknownKeys = true }
    private val client = HttpClient(CIO) { install(WebSockets) }

    val connectionState    = MutableStateFlow<ConnectionState>(ConnectionState.Disconnected)
    val pcResources        = MutableStateFlow(PcResources())
    val pcMedia            = MutableStateFlow(PcMedia())
    val pcNotifications    = MutableStateFlow<List<PcNotification>>(emptyList())
    val pcVolume           = MutableStateFlow<Int>(-1)
    val phoneNotifications = MutableStateFlow<List<PcNotification>>(emptyList())
    val wifiSignal          = MutableStateFlow(-1)
    val terminalOutput     = MutableSharedFlow<TerminalOutput>(replay = 1)
    val clipboard          = MutableStateFlow("")
    val fileReceived       = MutableStateFlow<Pair<String, String>?>(null)
    val processes          = MutableStateFlow<List<Map<String, Any>>>(emptyList())
    val apps               = MutableStateFlow<List<Map<String, String>>>(emptyList())
    val clipboardHistory   = MutableStateFlow<List<String>>(emptyList())

    @Volatile private var ignoreNextClipChange = false
    var onClipboardFromPc: (() -> Unit)? = null

    private var session    : DefaultWebSocketSession? = null
    private var connectJob : Job? = null
    private val scope      = CoroutineScope(Dispatchers.IO + SupervisorJob())

    var appContext: Context? = null

    var lastIp   = ""
        private set
    var lastPort = WS_PORT
        private set

    fun connect(ip: String, port: Int) {
        lastIp   = ip
        lastPort = port
        connectJob?.cancel()
        connectionState.value = ConnectionState.Connecting
        Log.i(TAG, "Conectando a ws://$ip:$port/ws")
        connectJob = scope.launch {
            try {
                client.webSocket(host = ip, port = port, path = "/ws") {
                    session = this
                    Log.i(TAG, "✓ Conectado a $ip:$port")
                    send(Frame.Text(json.encodeToString(WsMessage("ping", ""))))
                    for (frame in incoming) {
                        if (frame !is Frame.Text) continue
                        handleMessage(frame.readText())
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Desconectado: ${e.message}")
            } finally {
                session = null
                connectionState.value = ConnectionState.Disconnected
            }
        }
    }

    fun disconnect() {
        lastIp = ""
        lastPort = WS_PORT
        connectJob?.cancel()
        scope.launch { try { session?.close(CloseReason(CloseReason.Codes.NORMAL, "OK")) } catch (_: Exception) {} }
        session = null
        connectionState.value    = ConnectionState.Disconnected
        pcResources.value        = PcResources()
        pcMedia.value            = PcMedia()
        pcNotifications.value    = emptyList()
        pcVolume.value           = -1
        phoneNotifications.value = emptyList()
    }

    fun isConnected() = connectionState.value is ConnectionState.Connected
    fun isConnectedOrConnecting() = connectionState.value is ConnectionState.Connected
            || connectionState.value is ConnectionState.Connecting

    private fun sendJson(type: String, payload: String) = send(WsMessage(type, payload))

    private fun send(msg: WsMessage) {
        scope.launch {
            try { session?.send(Frame.Text(json.encodeToString(msg))) }
            catch (e: Exception) { Log.e(TAG, "Send: ${e.message}") }
        }
    }

    fun sendMediaCommand(action: String)   = sendJson("media_command",         """{"action":"$action"}""")
    fun sendTerminalCommand(cmd: String)   = sendJson("terminal",               """{"command":${json.encodeToString(cmd)}}""")
    fun sendClipboard(text: String)        = sendJson("clipboard_set",          """{"text":${json.encodeToString(text)}}""")
    fun sendMouseMove(dx: Int, dy: Int)    = sendJson("mouse_move",             """{"dx":$dx,"dy":$dy}""")
    fun sendMouseClick(button: String)     = sendJson("mouse_click",            """{"button":"$button"}""")
    fun sendMouseScroll(direction: String) = sendJson("mouse_scroll",           """{"direction":"$direction"}""")
    fun sendKeyPress(key: String)          = sendJson("key_press",              """{"key":"$key"}""")
    fun sendTypeText(text: String)         = sendJson("type_text",              """{"text":${json.encodeToString(text)}}""")
    fun requestProcesses()                 = sendJson("get_processes",          "")
    fun killProcess(pid: Int)              = sendJson("kill_process",           """{"pid":$pid}""")
    fun requestApps()                      = sendJson("get_apps",               "")
    fun launchApp(exec: String)            = sendJson("launch_app",             """{"exec":${json.encodeToString(exec)}}""")
    fun requestClipboardHistory()          = sendJson("get_clipboard_history",  "")
    fun requestBrightness()                = sendJson("get_brightness",         "")
    fun setBrightness(v: Int)              = sendJson("set_brightness",         """{"value":$v}""")
    fun sendPresentationCmd(a: String)     = sendJson("presentation",           """{"action":"$a"}""")
    fun sendWifiSignal(rssi: Int)           = sendJson("wifi_signal",            """{"rssi":$rssi}""")
    fun sendBattery(pct: Int, charging: Boolean) = sendJson("battery",             """{"pct":$pct,"charging":$charging}""")
    fun sendPhoneMedia(title: String, artist: String, playing: Boolean) =
        sendJson("phone_media", json.encodeToString(mapOf("title" to title, "artist" to artist, "playing" to playing.toString())))

    fun sendNotification(id: String, pkg: String, title: String, text: String) =
        sendJson("send_notification", json.encodeToString(mapOf("id" to id, "app" to pkg, "title" to title, "text" to text)))

    private fun handleMessage(raw: String) {
        try {
            val msg = json.decodeFromString<WsMessage>(raw)
            when (msg.type) {
                "pong"                -> Log.d(TAG, "pong")
                "pair_request"        -> handlePairRequest()
                "pair_accepted"       -> Log.i(TAG, "Pairing accepted by PC")
                "pair_rejected"       -> {
                    Log.w(TAG, "Pairing rejected by PC")
                    connectionState.value = ConnectionState.Error("Pairing rejected")
                    scope.launch { try { session?.close(CloseReason(CloseReason.Codes.NORMAL, "rejected")) } catch (_: Exception) {} }
                }
                "pc_info"             -> connectionState.value = ConnectionState.Connected(json.decodeFromString(msg.payload))
                "resources"           -> pcResources.value          = json.decodeFromString(msg.payload)
                "media"               -> pcMedia.value              = json.decodeFromString(msg.payload)
                "notifications"       -> pcNotifications.value      = json.decodeFromString(msg.payload)
                "phone_media_command" -> {
                    val act = org.json.JSONObject(msg.payload).optString("action", "")
                    handlePhoneMediaCommand(act)
                }
                "pc_volume"           -> {
                    val lvl = org.json.JSONObject(msg.payload).optInt("level", -1)
                    if (lvl >= 0) pcVolume.value = lvl
                }
                "phone_notifications" -> phoneNotifications.value   = json.decodeFromString(msg.payload)
                "terminal_output"     -> scope.launch { terminalOutput.emit(json.decodeFromString(msg.payload)) }
                "wifi_signal_ack"     -> { /* ignorar */ }
                "clipboard"           -> handleClipboardFromPc(msg.payload)
                "file_send"           -> handleFileFromPc(msg.payload)
                "processes"           -> handleProcesses(msg.payload)
                "apps"                -> handleApps(msg.payload)
                "clipboard_history"   -> handleClipboardHistory(msg.payload)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Parse: ${e.message}")
        }
    }

    private fun handlePhoneMediaCommand(action: String) {
        scope.launch {
            try {
                val am = context.getSystemService(android.content.Context.AUDIO_SERVICE) as android.media.AudioManager
                when (action) {
                    "play_pause" -> am.dispatchMediaKeyEvent(android.view.KeyEvent(android.view.KeyEvent.ACTION_DOWN, android.view.KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE))
                    "next"       -> am.dispatchMediaKeyEvent(android.view.KeyEvent(android.view.KeyEvent.ACTION_DOWN, android.view.KeyEvent.KEYCODE_MEDIA_NEXT))
                    "prev"       -> am.dispatchMediaKeyEvent(android.view.KeyEvent(android.view.KeyEvent.ACTION_DOWN, android.view.KeyEvent.KEYCODE_MEDIA_PREVIOUS))
                    "vol_up"     -> {
                        am.adjustStreamVolume(android.media.AudioManager.STREAM_MUSIC, android.media.AudioManager.ADJUST_RAISE, 0)
                        sendPhoneVolume(am)
                    }
                    "vol_down"   -> {
                        am.adjustStreamVolume(android.media.AudioManager.STREAM_MUSIC, android.media.AudioManager.ADJUST_LOWER, 0)
                        sendPhoneVolume(am)
                    }
                }
            } catch (e: Exception) {
                android.util.Log.e(TAG, "phone_media_command: ${e.message}")
            }
        }
    }

    private fun sendPhoneVolume(am: android.media.AudioManager) {
        val cur = am.getStreamVolume(android.media.AudioManager.STREAM_MUSIC)
        val max = am.getStreamMaxVolume(android.media.AudioManager.STREAM_MUSIC)
        val pct = if (max > 0) (cur * 100 / max) else 0
        sendJson("phone_volume", """{"level":$pct}""")
    }

    private fun handlePairRequest() {
        scope.launch {
            try {
                session?.send(Frame.Text(json.encodeToString(
                    WsMessage("pair_response", """{"accepted":true}""")
                )))
                Log.i(TAG, "pair_response sent")
            } catch (e: Exception) {
                Log.e(TAG, "pair_response: ${e.message}")
            }
        }
    }

    private fun handleClipboardFromPc(payload: String) {
        try {
            val obj  = org.json.JSONObject(payload)
            val text = obj.optString("text").takeIf { it.isNotEmpty() } ?: return
            if (text == clipboard.value) return

            ignoreNextClipChange = true
            onClipboardFromPc?.invoke()

            clipboard.value = text
            Log.d(TAG, "Portapapeles PC→Android: ${text.take(40)}")
            appContext?.let { ctx ->
                val cm = ctx.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                cm.setPrimaryClip(ClipData.newPlainText("Yelena", text))
            }
        } catch (e: Exception) { Log.e(TAG, "clipboard: ${e.message}") }
    }

    fun shouldIgnoreNextClipChange(): Boolean {
        return if (ignoreNextClipChange) {
            ignoreNextClipChange = false; true
        } else false
    }

    private fun handleFileFromPc(payload: String) {
        scope.launch(Dispatchers.IO) {
            try {
                val obj   = org.json.JSONObject(payload)
                val name  = obj.optString("name", "archivo")
                val b64   = obj.optString("data", "")
                if (b64.isEmpty()) return@launch
                val bytes = Base64.decode(b64, Base64.DEFAULT)
                val ctx   = appContext ?: return@launch
                val path: String
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    val values = ContentValues().apply {
                        put(MediaStore.Downloads.DISPLAY_NAME, name)
                        put(MediaStore.Downloads.IS_PENDING, 1)
                    }
                    val uri = ctx.contentResolver.insert(
                        MediaStore.Downloads.EXTERNAL_CONTENT_URI, values) ?: return@launch
                    ctx.contentResolver.openOutputStream(uri)?.use { it.write(bytes) }
                    values.clear(); values.put(MediaStore.Downloads.IS_PENDING, 0)
                    ctx.contentResolver.update(uri, values, null, null)
                    path = "Descargas/$name"
                } else {
                    val f = File(Environment.getExternalStoragePublicDirectory(
                        Environment.DIRECTORY_DOWNLOADS), name)
                    f.writeBytes(bytes); path = f.absolutePath
                }
                Log.i(TAG, "✓ Archivo: $path")
                fileReceived.value = Pair(name, path)
            } catch (e: Exception) { Log.e(TAG, "file: ${e.message}") }
        }
    }

    private fun handleProcesses(payload: String) {
        try {
            val arr = org.json.JSONArray(payload)
            processes.value = (0 until arr.length()).map { i ->
                val o = arr.getJSONObject(i)
                mapOf("pid" to o.getInt("pid"), "name" to o.getString("name"),
                      "cpu" to o.getDouble("cpu"), "mem" to o.getDouble("mem"))
            }
        } catch (e: Exception) { Log.e(TAG, "processes: ${e.message}") }
    }

    private fun handleApps(payload: String) {
        try {
            val arr = org.json.JSONArray(payload)
            apps.value = (0 until arr.length()).map { i ->
                val o = arr.getJSONObject(i)
                mapOf("name" to o.optString("name"), "exec" to o.optString("exec"))
            }
        } catch (e: Exception) { Log.e(TAG, "apps: ${e.message}") }
    }

    private fun handleClipboardHistory(payload: String) {
        try {
            val arr = org.json.JSONObject(payload).getJSONArray("items")
            clipboardHistory.value = (0 until arr.length()).map { arr.getString(it) }
        } catch (e: Exception) { Log.e(TAG, "history: ${e.message}") }
    }
}
package org.cuerdos.yelena.network

import android.util.Log
import kotlinx.coroutines.flow.MutableStateFlow
import org.json.JSONObject
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.NetworkInterface
import kotlin.concurrent.thread

data class DiscoveredDevice(val name: String, val ip: String, val port: Int, val os: String)

object YelenaDiscovery {
    private const val TAG       = "YelenaDiscovery"
    const val  UDP_PORT         = 1716
    private const val INTERVAL  = 3000L
    private const val TIMEOUT_MS = 10_000L

    val devices   = MutableStateFlow<List<DiscoveredDevice>>(emptyList())
    val isRunning = MutableStateFlow(false)

    private var sendSocket: DatagramSocket? = null
    private var recvSocket: DatagramSocket? = null
    private val found    = mutableMapOf<String, DiscoveredDevice>()
    private val lastSeen = mutableMapOf<String, Long>()
    @Volatile private var running = false

    fun start() {
        if (running) return
        running = true
        isRunning.value = true

        thread(isDaemon = true, name = "Yelena-Send") {
            try {
                sendSocket = DatagramSocket().also { it.broadcast = true }
                while (running) {
                    trySend()
                    pruneStale()
                    Thread.sleep(INTERVAL)
                }
            } catch (e: Exception) {
                Log.e(TAG, "Send thread error: ${e.message}")
            } finally {
                sendSocket?.close(); sendSocket = null
            }
        }

        thread(isDaemon = true, name = "Yelena-Recv") {
            try {
                recvSocket = DatagramSocket(null).also { sock ->
                    sock.reuseAddress = true
                    sock.broadcast    = true
                    sock.bind(InetSocketAddress(UDP_PORT))
                    sock.soTimeout    = 2000
                }
                val buf  = ByteArray(4096)
                val myIp = getLocalIp()

                while (running) {
                    try {
                        val pkt = DatagramPacket(buf, buf.size)
                        recvSocket?.receive(pkt)
                        val src = pkt.address.hostAddress ?: continue
                        val raw = String(pkt.data, 0, pkt.length)
                        if (src == myIp) continue
                        handlePacket(src, raw)
                    } catch (_: java.net.SocketTimeoutException) {
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Recv thread error: ${e.message}", e)
            } finally {
                recvSocket?.close(); recvSocket = null
            }
        }
    }

    fun stop() {
        running = false
        isRunning.value = false
        sendSocket?.close(); sendSocket = null
        recvSocket?.close(); recvSocket = null
        found.clear()
        lastSeen.clear()
        devices.value = emptyList()
    }

    private fun getBroadcastAddr(): String {
        val ip = getLocalIp()
        val parts = ip.split(".")
        return if (parts.size == 4) "${parts[0]}.${parts[1]}.${parts[2]}.255"
        else "255.255.255.255"
    }

    private fun trySend() {
        val ip = getLocalIp()
        if (ip.isEmpty()) return

        val payload = JSONObject().apply {
            put("type",         "yelena")
            put("name",         android.os.Build.MODEL)
            put("manufacturer", android.os.Build.MANUFACTURER)
            put("ip",           ip)
            put("port",         8766)
            put("os",           "Android ${android.os.Build.VERSION.RELEASE}")
            put("version",      "1")
            put("role",         "android")
        }.toString().toByteArray(Charsets.UTF_8)

        try {
            val bcast = getBroadcastAddr()
            listOf(bcast, "255.255.255.255").forEach { addr ->
                val dest = InetAddress.getByName(addr)
                sendSocket?.send(DatagramPacket(payload, payload.size, dest, UDP_PORT))
            }
        } catch (e: Exception) {
            Log.w(TAG, "Broadcast send failed: ${e.message}")
        }
    }

    private fun pruneStale() {
        val now = System.currentTimeMillis()
        val stale = lastSeen.entries.filter { now - it.value > TIMEOUT_MS }.map { it.key }
        if (stale.isEmpty()) return
        stale.forEach { ip ->
            found.remove(ip)
            lastSeen.remove(ip)
            Log.d(TAG, "Device expired: $ip")
        }
        devices.value = found.values.toList()
    }

    private fun handlePacket(src: String, raw: String) {
        try {
            val j    = JSONObject(raw)
            if (j.optString("type") != "yelena") return
            val role = j.optString("role", "")
            if (role == "android") return
            val os   = j.optString("os", "")

            val name  = j.optString("name", src)
            val port  = j.optInt("port", 8765)
            val isNew = src !in found
            found[src]    = DiscoveredDevice(name, src, port, os)
            lastSeen[src] = System.currentTimeMillis()
            devices.value = found.values.toList()
            if (isNew) Log.i(TAG, "PC found: $name @ $src:$port")
        } catch (e: Exception) {
            Log.e(TAG, "Parse error: ${e.message}")
        }
    }

    fun getLocalIp(): String {
        try {
            NetworkInterface.getNetworkInterfaces()?.toList()?.forEach { iface ->
                if (!iface.isUp || iface.isLoopback || iface.isVirtual) return@forEach
                iface.inetAddresses?.toList()?.forEach { addr ->
                    if (!addr.isLoopbackAddress && addr is java.net.Inet4Address) {
                        val ip = addr.hostAddress ?: return@forEach
                        if (!ip.startsWith("169.254")) return ip
                    }
                }
            }
        } catch (_: Exception) { }
        return ""
    }
}
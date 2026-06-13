package org.cuerdos.yelena

import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import org.cuerdos.yelena.websocket.YelenaWebSocket

class YelenaNotificationListener : NotificationListenerService() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        val extras = sbn.notification.extras
        val title  = extras.getString("android.title") ?: return
        val text   = extras.getCharSequence("android.text")?.toString() ?: ""
        val pkg    = sbn.packageName ?: "unknown"
        val id     = sbn.id.toString()
        scope.launch {
            YelenaWebSocket.sendNotification(id, pkg, title, text)
        }
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification) {}
}
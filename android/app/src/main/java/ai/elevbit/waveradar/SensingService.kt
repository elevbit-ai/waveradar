// WaveRadar — foreground sampler for the phone's own router link.
// Author: Joaquim Pedro de Morais Filho <j360074@hotmail.com>
// License: MIT

package ai.elevbit.waveradar

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.graphics.drawable.Icon
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.PowerManager
import android.os.SystemClock
import ai.elevbit.waveradar.dsp.Frame
import ai.elevbit.waveradar.dsp.MotionState
import ai.elevbit.waveradar.dsp.Presence
import ai.elevbit.waveradar.sensing.WifiLinkReader

class SensingService : Service() {
    private val handler = Handler(Looper.getMainLooper())
    private lateinit var reader: WifiLinkReader
    private var wakeLock: PowerManager.WakeLock? = null
    private var loopStarted = false
    private var lastNotifAt = 0L

    private val tick = object : Runnable {
        override fun run() {
            val snap = reader.read()
            if (!snap.online) {
                RadarBus.publishOffline()
            } else {
                val t = System.currentTimeMillis() / 1000.0
                RadarBus.engine.push(Frame(t, snap.rssiDbm.toDouble()))
                val state = RadarBus.engine.state()
                RadarBus.publish(state, snap)
                val now = SystemClock.elapsedRealtime()
                if (now - lastNotifAt > 2000L) {
                    lastNotifAt = now
                    val nm = getSystemService(NotificationManager::class.java)
                    nm.notify(NOTIF_ID, buildNotification(state))
                }
            }
            handler.postDelayed(this, SAMPLE_MS)
        }
    }

    override fun onCreate() {
        super.onCreate()
        reader = WifiLinkReader(this)
        createChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            stopSelf()
            return START_NOT_STICKY
        }
        val notification = buildNotification(RadarBus.motion.value)
        if (Build.VERSION.SDK_INT >= 34) {
            startForeground(NOTIF_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE)
        } else {
            startForeground(NOTIF_ID, notification)
        }
        if (!loopStarted) {
            loopStarted = true
            acquireWakeLock()
            handler.post(tick)
        }
        RadarBus.running.value = true
        return START_STICKY
    }

    override fun onDestroy() {
        handler.removeCallbacks(tick)
        loopStarted = false
        wakeLock?.let { if (it.isHeld) it.release() }
        wakeLock = null
        RadarBus.running.value = false
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun acquireWakeLock() {
        val pm = getSystemService(PowerManager::class.java)
        wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "waveradar:rssi").apply {
            setReferenceCounted(false)
            acquire()
        }
    }

    private fun createChannel() {
        val nm = getSystemService(NotificationManager::class.java)
        val channel = NotificationChannel(
            CHANNEL_ID,
            "Monitoramento do enlace",
            NotificationManager.IMPORTANCE_LOW,
        ).apply {
            description = "Presença estimada pelo RSSI do Wi-Fi deste telefone."
            setShowBadge(false)
        }
        nm.createNotificationChannel(channel)
    }

    private fun buildNotification(state: MotionState): Notification {
        val open = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val stop = PendingIntent.getService(
            this,
            1,
            Intent(this, SensingService::class.java).setAction(ACTION_STOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val text = when {
            !RadarBus.link.value.online -> "Sem Wi-Fi. Conecte-se ao seu roteador."
            else -> when (state.presence) {
                Presence.CALIBRATING -> "Calibrando o enlace. Fique imóvel."
                Presence.CLEAR -> "Vazio — nenhum movimento recente no enlace."
                Presence.PRESENT -> "Presente — houve movimento e o tempo de retenção segue."
                Presence.MOVING -> "Em movimento no enlace com o roteador."
            }
        }
        return Notification.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_stat_radar)
            .setContentTitle("WaveRadar")
            .setContentText(text)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setContentIntent(open)
            .addAction(
                Notification.Action.Builder(
                    Icon.createWithResource(this, R.drawable.ic_stat_radar),
                    "Parar",
                    stop,
                ).build(),
            )
            .build()
    }

    companion object {
        const val ACTION_STOP = "ai.elevbit.waveradar.STOP"
        private const val CHANNEL_ID = "waveradar_link"
        private const val NOTIF_ID = 8347
        private const val SAMPLE_MS = 200L

        fun start(context: Context) {
            val intent = Intent(context, SensingService::class.java)
            context.startForegroundService(intent)
        }
    }
}

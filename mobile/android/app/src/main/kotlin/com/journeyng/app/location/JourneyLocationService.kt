package com.journeyng.app.location

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority

/**
 * Foreground location service (spec §15, §16).
 *
 * Started only from a visible user action (START JOURNEY). Shows a persistent
 * transparency notification while sharing. Movement-aware update intervals
 * (spec §14). Stops safely on stop-sharing/arrival/expiration.
 */
class JourneyLocationService : Service() {

    private val fusedLocationClient by lazy {
        LocationServices.getFusedLocationProviderClient(this)
    }

    private var callback: LocationCallback? = null
    private var currentIntervalMs: Long = DEFAULT_INTERVAL_MS

    override fun onCreate() {
        super.onCreate()
        createChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_START -> {
                val viewerName = intent.getStringExtra(EXTRA_VIEWER_NAME) ?: "your host"
                startForeground(NOTIFICATION_ID, buildNotification(viewerName))
                startLocationUpdates()
            }
            ACTION_SET_INTERVAL -> {
                val interval = intent.getLongExtra(EXTRA_INTERVAL_MS, DEFAULT_INTERVAL_MS)
                if (interval != currentIntervalMs) {
                    currentIntervalMs = interval
                    startLocationUpdates()
                }
            }
            ACTION_STOP -> stopSharing()
        }
        return START_NOT_STICKY
    }

    private fun startLocationUpdates() {
        callback?.let { fusedLocationClient.removeLocationUpdates(it) }

        val request = LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, currentIntervalMs)
            .setMinUpdateDistanceMeters(5f)
            .setWaitForAccurateLocation(false)
            .build()

        callback = object : LocationCallback() {
            override fun onLocationResult(result: LocationResult) {
                val location = result.lastLocation ?: return
                LocationEventBridge.emit(
                    latitude = location.latitude,
                    longitude = location.longitude,
                    accuracyM = location.accuracy.toDouble(),
                    speedMps = if (location.hasSpeed()) location.speed.toDouble() else null,
                    heading = if (location.hasBearing()) location.bearing.toDouble() else null,
                    altitudeM = if (location.hasAltitude()) location.altitude else null,
                    recordedAtMs = location.time,
                )
            }
        }

        try {
            fusedLocationClient.requestLocationUpdates(
                request, callback!!, mainLooper
            )
        } catch (_: SecurityException) {
            // Permission revoked mid-journey: stop safely rather than crash.
            stopSharing()
        }
    }

    private fun buildNotification(viewerName: String): Notification {
        val openIntent = PendingIntent.getActivity(
            this, 0,
            packageManager.getLaunchIntentForPackage(packageName),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val stopIntent = PendingIntent.getService(
            this, 1,
            Intent(this, JourneyLocationService::class.java).setAction(ACTION_STOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Journey active")
            .setContentText("Your location is being shared with $viewerName.")
            .setSmallIcon(android.R.drawable.ic_menu_mylocation)
            .setOngoing(true)
            .setContentIntent(openIntent)
            .addAction(0, "Stop Sharing", stopIntent)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .build()
    }

    private fun stopSharing() {
        callback?.let { fusedLocationClient.removeLocationUpdates(it) }
        callback = null
        LocationEventBridge.emitStopped()
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    override fun onDestroy() {
        callback?.let { try { fusedLocationClient.removeLocationUpdates(it) } catch (_: Exception) {} }
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun createChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID, "Active journey", NotificationManager.IMPORTANCE_LOW
            ).apply { description = "Shown while your location is being shared" }
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
    }

    companion object {
        const val CHANNEL_ID = "journeyng"
        const val NOTIFICATION_ID = 42
        const val ACTION_START = "com.journeyng.app.START"
        const val ACTION_STOP = "com.journeyng.app.STOP"
        const val ACTION_SET_INTERVAL = "com.journeyng.app.SET_INTERVAL"
        const val EXTRA_VIEWER_NAME = "viewer_name"
        const val EXTRA_INTERVAL_MS = "interval_ms"
        const val DEFAULT_INTERVAL_MS = 5000L
    }
}

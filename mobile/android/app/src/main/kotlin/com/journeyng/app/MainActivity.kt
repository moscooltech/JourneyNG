package com.journeyng.app

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.journeyng.app.location.JourneyLocationService
import com.journeyng.app.location.LocationEventBridge
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {

    private val methodChannelName = "journey/location_service"
    private val eventChannelName = "journey/location_events"

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, methodChannelName)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "start" -> {
                        val viewerName = call.argument<String>("viewer_name") ?: "your host"
                        val ok = startSharing(viewerName)
                        if (ok) result.success(true) else result.error("PERMISSION_DENIED", "Location permission not granted", null)
                    }
                    "stop" -> {
                        stopService(Intent(this, JourneyLocationService::class.java))
                        result.success(true)
                    }
                    "isRunning" -> result.success(true)
                    else -> result.notImplemented()
                }
            }

        EventChannel(flutterEngine.dartExecutor.binaryMessenger, eventChannelName)
            .setStreamHandler(object : EventChannel.StreamHandler {
                override fun onListen(args: Any?, events: EventChannel.EventSink?) {
                    LocationEventBridge.attach(events)
                }
                override fun onCancel(args: Any?) {
                    LocationEventBridge.attach(null)
                }
            })
    }

    private fun hasLocationPermission(): Boolean {
        val fine = ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION)
        val coarse = ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_COARSE_LOCATION)
        return fine == PackageManager.PERMISSION_GRANTED || coarse == PackageManager.PERMISSION_GRANTED
    }

    private fun startSharing(viewerName: String): Boolean {
        if (!hasLocationPermission()) return false
        val intent = Intent(this, JourneyLocationService::class.java).apply {
            action = JourneyLocationService.ACTION_START
            putExtra(JourneyLocationService.EXTRA_VIEWER_NAME, viewerName)
        }
        ContextCompat.startForegroundService(this, intent)
        return true
    }
}

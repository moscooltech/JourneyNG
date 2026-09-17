package com.journeyng.app.location

import io.flutter.plugin.common.EventChannel

/// Bridges native location events to Flutter through an EventChannel sink.
/// Thread-safe: events are emitted from the service, consumed on the Flutter side.
object LocationEventBridge {
    @Volatile private var sink: EventChannel.EventSink? = null

    fun attach(newSink: EventChannel.EventSink?) {
        sink = newSink
    }

    fun emit(
        latitude: Double,
        longitude: Double,
        accuracyM: Double,
        speedMps: Double?,
        heading: Double?,
        altitudeM: Double?,
        recordedAtMs: Long,
    ) {
        sink?.success(
            mapOf(
                "type" to "location",
                "latitude" to latitude,
                "longitude" to longitude,
                "accuracy_m" to accuracyM,
                "speed_mps" to speedMps,
                "heading" to heading,
                "altitude_m" to altitudeM,
                "recorded_at_ms" to recordedAtMs,
            )
        )
    }

    fun emitStopped() {
        sink?.success(mapOf("type" to "stopped"))
    }
}

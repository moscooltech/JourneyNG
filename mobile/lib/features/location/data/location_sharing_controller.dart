import 'dart:async';

import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/config.dart';
import '../../journeys/data/journey_repository.dart';

/// Bridges the native Kotlin foreground service to Flutter (spec §15).
///
/// Flow: service events -> validation -> upload via JourneyRepository.
/// Movement-aware interval adjustment (spec §14) is sent back to the service.
final locationSharingControllerProvider =
    Provider<LocationSharingController>((ref) {
  return LocationSharingController(ref.watch(journeyRepositoryProvider));
});

class LocationSharingController {
  LocationSharingController(this._repo);

  static const _method = MethodChannel('journey/location_service');
  static const _events = EventChannel('journey/location_events');

  final JourneyRepository _repo;
  StreamSubscription? _sub;
  Timer? _uploadThrottle;
  double? _lastLat;
  double? _lastLng;
  String? _activeJourneyId;

  bool _sharing = false;
  bool get isSharing => _sharing;

  Future<bool> start({required String journeyId, required String viewerName}) async {
    _activeJourneyId = journeyId;
    try {
      final ok = await _method.invokeMethod<bool>('start', {'viewer_name': viewerName});
      if (ok != true) return false;
      _listen();
      _sharing = true;
      return true;
    } on PlatformException {
      // Permission denied or service refused — never claim success (spec §15).
      return false;
    }
  }

  Future<void> stop() async {
    _sub?.cancel();
    _sub = null;
    _uploadThrottle?.cancel();
    try {
      await _method.invokeMethod('stop');
    } on PlatformException {/* service already gone */}
    _sharing = false;
    _activeJourneyId = null;
  }

  void _listen() {
    _sub?.cancel();
    _sub = _events.receiveBroadcastStream().listen(
      _onEvent,
      onError: (_) {/* stream error: host sees stale state server-side */},
    );
  }

  void _onEvent(dynamic event) {
    if (event is! Map) return;
    if (event['type'] == 'stopped') {
      _sharing = false;
      return;
    }
    if (event['type'] == 'location' && _activeJourneyId != null) {
      final lat = (event['latitude'] as num).toDouble();
      final lng = (event['longitude'] as num).toDouble();
      final accuracy = (event['accuracy_m'] as num?)?.toDouble();
      final speed = (event['speed_mps'] as num?)?.toDouble();
      final heading = (event['heading'] as num?)?.toDouble();
      final recordedMs = event['recorded_at_ms'] as int?;

      // Movement-aware upload interval (spec §14).
      _adjustInterval(speed);

      // Throttle: coalesce bursts; latest location wins (spec §17: no backlog).
      _uploadThrottle?.cancel();
      _uploadThrottle = Timer(const Duration(milliseconds: 300), () {
        _repo.uploadLocation(
          journeyId: _activeJourneyId!,
          latitude: lat,
          longitude: lng,
          accuracyM: accuracy,
          speedMps: speed,
          heading: heading,
          recordedAt: recordedMs != null
              ? DateTime.fromMillisecondsSinceEpoch(recordedMs, isUtc: true)
              : DateTime.now().toUtc(),
        ).catchError((_) {/* network lost: latest will be sent on reconnect */});
      });

      _lastLat = lat;
      _lastLng = lng;
    }
  }

  void _adjustInterval(double? speedMps) {
    // moving ~3-5s, normal 5-8s, stationary/slow 10-20s (spec §14).
    final interval = speedMps == null
        ? 5000
        : speedMps > 8
            ? 4000
            : speedMps > 1.5
                ? 6000
                : 15000;
    _method.invokeMethod('setInterval', {'interval_ms': interval}).catchError((_) => null);
  }

  /// Latest cached local location for UI (minimal transient state, spec §17).
  ({double lat, double lng})? get lastKnown {
    if (_lastLat == null || _lastLng == null) return null;
    return (lat: _lastLat!, lng: _lastLng!);
  }
}

// Exported for tests.
const kConfig = AppConfig;

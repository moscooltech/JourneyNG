import 'package:geolocator/geolocator.dart';

/// Location permission handling (spec §18).
///
/// OS dialogs are only opened AFTER an in-app explanation screen. Never call
/// [ensurePermission] without showing the consent explanation first.
class LocationPermissionHelper {
  /// Returns true when precise (or acceptable approximate) location is granted.
  static Future<LocationPermissionStatus> check() async {
    final serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) return LocationPermissionStatus.serviceDisabled;

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.denied) {
      return LocationPermissionStatus.denied;
    }
    if (permission == LocationPermission.deniedForever) {
      return LocationPermissionStatus.deniedForever;
    }
    if (permission == LocationPermission.unableToDetermine) {
      return LocationPermissionStatus.denied;
    }
    // whileInUse is sufficient for the foreground-service architecture (spec §18).
    return permission == LocationPermission.whileInUse
        ? LocationPermissionStatus.precise
        : LocationPermissionStatus.approximate;
  }

  static Future<Position> currentPosition() => Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(accuracy: LocationAccuracy.high),
      );
}

enum LocationPermissionStatus {
  precise,
  approximate,
  denied,
  deniedForever,
  serviceDisabled,
}

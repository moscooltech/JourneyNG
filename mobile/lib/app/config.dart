/// Environment-specific configuration.
///
/// Only PUBLIC values ship in the mobile build (API base URL, Mapbox public
/// token). Backend master secrets never belong here (spec §47).
class AppConfig {
  const AppConfig({
    required this.apiBaseUrl,
    required this.wsBaseUrl,
    required this.mapboxPublicToken,
    this.appEnv = 'development',
  });

  final String apiBaseUrl;
  final String wsBaseUrl;
  final String mapboxPublicToken;
  final String appEnv;

  static const AppConfig development = AppConfig(
    apiBaseUrl: 'http://10.0.2.2:8000/api/v1', // Android emulator -> host
    wsBaseUrl: 'ws://10.0.2.2:8000/ws',
    mapboxPublicToken: String.fromEnvironment(
      'MAPBOX_PUBLIC_TOKEN',
      defaultValue: '',
    ),
    appEnv: 'development',
  );

  static const AppConfig production = AppConfig(
    apiBaseUrl: 'https://api.example.com/api/v1',
    wsBaseUrl: 'wss://api.example.com/ws',
    mapboxPublicToken: String.fromEnvironment(
      'MAPBOX_PUBLIC_TOKEN',
      defaultValue: '',
    ),
    appEnv: 'production',
  );

  static const AppConfig current = development;
}

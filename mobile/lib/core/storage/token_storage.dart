import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Secure local storage for auth/guest tokens (spec §3: secure local storage).
final tokenStorageProvider = Provider<TokenStorage>((ref) => TokenStorage());

class TokenStorage {
  static const _storage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
  );

  static const _kAccess = 'access_token';
  static const _kRefresh = 'refresh_token';
  static const _kGuest = 'guest_token';

  String? accessToken;
  String? refreshToken;
  String? guestToken;

  Future<void> load() async {
    accessToken = await _storage.read(key: _kAccess);
    refreshToken = await _storage.read(key: _kRefresh);
    guestToken = await _storage.read(key: _kGuest);
  }

  Future<void> saveSession({
    required String accessToken,
    required String refreshToken,
  }) async {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
    guestToken = null;
    await _storage.write(key: _kAccess, value: accessToken);
    await _storage.write(key: _kRefresh, value: refreshToken);
    await _storage.delete(key: _kGuest);
  }

  Future<void> saveGuestToken(String token) async {
    guestToken = token;
    await _storage.write(key: _kGuest, value: token);
  }

  Future<void> clear() async {
    accessToken = null;
    refreshToken = null;
    guestToken = null;
    await _storage.delete(key: _kAccess);
    await _storage.delete(key: _kRefresh);
    await _storage.delete(key: _kGuest);
  }
}

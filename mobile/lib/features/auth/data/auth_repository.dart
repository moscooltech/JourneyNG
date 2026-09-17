import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/errors/app_exception.dart';
import '../../../core/network/api_client.dart';
import '../../../core/storage/token_storage.dart';

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository(
    ref.watch(apiClientProvider),
    ref.watch(tokenStorageProvider),
  );
});

class AuthRepository {
  AuthRepository(this._client, this._tokens);

  final ApiClient _client;
  final TokenStorage _tokens;

  Future<void> register({
    required String displayName,
    required String email,
    required String password,
  }) async {
    try {
      final resp = await _client.post('/auth/register', data: {
        'display_name': displayName,
        'email': email,
        'phone': null,
        'password': password,
      });
      await _tokens.saveSession(
        accessToken: resp.data['access_token'] as String,
        refreshToken: resp.data['refresh_token'] as String,
      );
    } catch (e) {
      throw AppException.fromDioError(e);
    }
  }

  Future<void> login({
    required String identifier,
    required String password,
  }) async {
    try {
      final resp = await _client.post('/auth/login', data: {
        'identifier': identifier,
        'password': password,
      });
      await _tokens.saveSession(
        accessToken: resp.data['access_token'] as String,
        refreshToken: resp.data['refresh_token'] as String,
      );
    } catch (e) {
      throw AppException.fromDioError(e);
    }
  }

  Future<void> logout() async {
    final refresh = _tokens.refreshToken;
    if (refresh != null) {
      try {
        await _client.post('/auth/logout', data: {'refresh_token': refresh});
      } catch (_) {/* local logout proceeds */}
    }
    await _tokens.clear();
  }
}

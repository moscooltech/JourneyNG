import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../storage/token_storage.dart';
import '../../app/config.dart';

/// Central HTTP client. UI never touches Dio directly — repositories do.
final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient(ref.watch(tokenStorageProvider));
});

class ApiClient {
  ApiClient(this._tokens) : _dio = Dio(BaseOptions(
          baseUrl: AppConfig.current.apiBaseUrl,
          connectTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 15),
        )) {
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: _attachAuth,
      onError: (e, handler) async {
        // Single retry with refreshed token on 401 for registered users.
        if (e.response?.statusCode == 401 && _tokens.refreshToken != null) {
          final refreshed = await _tryRefresh();
          if (refreshed) {
            final response = await _retry(e.requestOptions);
            return handler.resolve(response);
          }
        }
        handler.next(e);
      },
    ));
  }

  final TokenStorage _tokens;
  final Dio _dio;

  Future<void> _attachAuth(options, handler) async {
    if (_tokens.guestToken != null) {
      options.headers['X-Guest-Token'] = _tokens.guestToken;
    } else if (_tokens.accessToken != null) {
      options.headers['Authorization'] = 'Bearer ${_tokens.accessToken}';
    }
    handler.next(options);
  }

  Future<bool> _tryRefresh() async {
    final refresh = _tokens.refreshToken;
    if (refresh == null) return false;
    try {
      final resp = await Dio(BaseOptions(baseUrl: AppConfig.current.apiBaseUrl))
          .post('/auth/refresh', data: {'refresh_token': refresh});
      await _tokens.saveSession(
        accessToken: resp.data['access_token'] as String,
        refreshToken: resp.data['refresh_token'] as String,
      );
      return true;
    } catch (_) {
      await _tokens.clear();
      return false;
    }
  }

  Future<Response<dynamic>> _retry(RequestOptions requestOptions) async {
    final options = Options(
      method: requestOptions.method,
      headers: {
        ...requestOptions.headers,
        'Authorization': 'Bearer ${_tokens.accessToken}',
      },
    );
    return _dio.request(
      requestOptions.path,
      data: requestOptions.data,
      queryParameters: requestOptions.queryParameters,
      options: options,
    );
  }

  Future<Response<dynamic>> get(String path, {Map<String, dynamic>? query}) =>
      _dio.get(path, queryParameters: query);

  Future<Response<dynamic>> post(String path, {Object? data}) =>
      _dio.post(path, data: data);

  Future<Response<dynamic>> patch(String path, {Object? data}) =>
      _dio.patch(path, data: data);

  Future<Response<dynamic>> delete(String path) => _dio.delete(path);
}

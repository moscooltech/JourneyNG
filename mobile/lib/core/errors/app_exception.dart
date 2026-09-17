/// Client-side error model matching the backend envelope:
/// {error: {code, message, request_id}}
class AppException implements Exception {
  const AppException({
    required this.code,
    required this.message,
    this.requestId,
    this.statusCode,
  });

  final String code;
  final String message;
  final String? requestId;
  final int? statusCode;

  bool get isUnauthenticated => code == 'UNAUTHENTICATED';
  bool get isRateLimited => code == 'RATE_LIMITED';

  @override
  String toString() => message;

  static AppException fromDioError(dynamic error) {
    final response = error.response;
    if (response?.data is Map) {
      final err = (response.data as Map)['error'];
      if (err is Map) {
        return AppException(
          code: err['code']?.toString() ?? 'UNKNOWN',
          message: err['message']?.toString() ?? 'Something went wrong.',
          requestId: err['request_id']?.toString(),
          statusCode: response.statusCode,
        );
      }
    }
    return const AppException(
      code: 'NETWORK_ERROR',
      message: 'Connection unavailable. Please check your internet.',
    );
  }
}

import 'package:flutter_test/flutter_test.dart';

import 'package:journeyng/core/errors/app_exception.dart';

void main() {
  group('AppException', () {
    test('parses backend error envelope', () {
      const exc = AppException(
        code: 'CONSENT_REQUIRED',
        message: 'Location sharing consent has not been granted.',
        statusCode: 403,
      );
      expect(exc.code, 'CONSENT_REQUIRED');
      expect(exc.isUnauthenticated, isFalse);
      expect(exc.toString(), contains('consent'));
    });

    test('network fallback message is plain-language', () {
      const exc = AppException(
        code: 'NETWORK_ERROR',
        message: 'Connection unavailable. Please check your internet.',
      );
      expect(exc.message, isNot(contains('tracking')));
    });
  });
}

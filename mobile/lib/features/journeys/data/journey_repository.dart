import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/errors/app_exception.dart';
import '../../../core/network/api_client.dart';
import '../../../core/storage/token_storage.dart';

final journeyRepositoryProvider = Provider<JourneyRepository>((ref) {
  return JourneyRepository(
    ref.watch(apiClientProvider),
    ref.watch(tokenStorageProvider),
  );
});

class JourneyRepository {
  JourneyRepository(this _client, this _tokens);

  final ApiClient _client;
  final TokenStorage _tokens;

  Future<Map<String, dynamic>> createJourney({
    required String? destinationName,
    required double latitude,
    required double longitude,
    required int expiresInMinutes,
  }) async {
    try {
      final resp = await _client.post('/journeys', data: {
        'destination': {
          'name': destinationName,
          'latitude': latitude,
          'longitude': longitude,
        },
        'expires_in_minutes': expiresInMinutes,
      });
      return Map<String, dynamic>.from(resp.data as Map);
    } catch (e) {
      throw AppException.fromDioError(e);
    }
  }

  Future<String> createInvitation(String journeyId,
      {int? maxUses, int expiresInMinutes = 120}) async {
    try {
      final resp = await _client.post('/journeys/$journeyId/invitations', data: {
        'max_uses': maxUses,
        'expires_in_minutes': expiresInMinutes,
      });
      return resp.data['invite_url'] as String;
    } catch (e) {
      throw AppException.fromDioError(e);
    }
  }

  Future<void> startJourney(String journeyId) async {
    try {
      await _client.post('/journeys/$journeyId/start');
    } catch (e) {
      throw AppException.fromDioError(e);
    }
  }

  Future<void> endJourney(String journeyId) async {
    try {
      await _client.post('/journeys/$journeyId/complete');
    } catch (e) {
      throw AppException.fromDioError(e);
    }
  }

  Future<Map<String, dynamic>> getJourney(String journeyId) async {
    try {
      final resp = await _client.get('/journeys/$journeyId');
      return Map<String, dynamic>.from(resp.data as Map);
    } catch (e) {
      throw AppException.fromDioError(e);
    }
  }

  Future<List<Map<String, dynamic>>> getLocations(String journeyId) async {
    try {
      final resp = await _client.get('/journeys/$journeyId/locations');
      return (resp.data as List)
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList();
    } catch (e) {
      throw AppException.fromDioError(e);
    }
  }

  // --- Visitor actions ---

  Future<String> joinAsGuest(String rawToken, String displayName) async {
    try {
      final resp = await _client.post('/join/$rawToken/guest', data: {
        'display_name': displayName,
      });
      final token = resp.data['guest_token'] as String;
      await _tokens.saveGuestToken(token);
      return resp.data['journey_id'] as String;
    } catch (e) {
      throw AppException.fromDioError(e);
    }
  }

  Future<void> grantConsent(String journeyId) async {
    try {
      await _client.post('/journeys/$journeyId/consent', data: {
        'scope': 'LIVE_LOCATION',
        'purpose': 'TRAVEL_TO_DESTINATION',
        'duration': 'UNTIL_ARRIVAL',
      });
    } catch (e) {
      throw AppException.fromDioError(e);
    }
  }

  Future<void> startSharing(String journeyId) async {
    try {
      await _client.post('/journeys/$journeyId/participants/me/start');
    } catch (e) {
      throw AppException.fromDioError(e);
    }
  }

  Future<void> stopSharing(String journeyId) async {
    try {
      await _client.post('/journeys/$journeyId/consent/revoke');
    } catch (e) {
      throw AppException.fromDioError(e);
    }
  }

  Future<void> markArrived(String journeyId) async {
    try {
      await _client.post('/journeys/$journeyId/participants/me/arrive');
    } catch (e) {
      throw AppException.fromDioError(e);
    }
  }

  Future<void> leave(String journeyId) async {
    try {
      await _client.post('/journeys/$journeyId/participants/me/leave');
    } catch (e) {
      throw AppException.fromDioError(e);
    }
  }

  Future<void> uploadLocation({
    required String journeyId,
    required double latitude,
    required double longitude,
    double? accuracyM,
    double? speedMps,
    double? heading,
    required DateTime recordedAt,
  }) async {
    await _client.post('/journeys/$journeyId/location', data: {
      'latitude': latitude,
      'longitude': longitude,
      'accuracy_m': accuracyM,
      'speed_mps': speedMps,
      'heading': heading,
      'recorded_at': recordedAt.toUtc().toIso8601String(),
    });
  }
}

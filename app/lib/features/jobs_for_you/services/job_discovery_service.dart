import 'package:dio/dio.dart';

import '../../../services/api_client.dart';

/// Job preferences (match-preferences API) + Jobs For You client (Phase 0).
class JobDiscoveryService {
  JobDiscoveryService({ApiClient? client}) : _client = client ?? apiClient;

  final ApiClient _client;

  Dio get _dio => _client.dio;

  Future<List<Map<String, dynamic>>> suggestTitles() async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/api/v1/match-preferences/suggestions',
    );
    final items = response.data?['suggestions'];
    if (items is! List) return [];
    return items
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
  }

  /// Null when the user has not saved preferences yet.
  Future<Map<String, dynamic>?> getPreferences() async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/api/v1/match-preferences',
    );
    final prefs = response.data?['preferences'];
    if (prefs is! Map) return null;
    return Map<String, dynamic>.from(prefs);
  }

  Future<Map<String, dynamic>> savePreferences({
    required List<String> titles,
    required List<String> seniorityBands,
    required String remotePreference,
    required List<String> countries,
    String? city,
  }) async {
    final response = await _dio.put<Map<String, dynamic>>(
      '/api/v1/match-preferences',
      data: {
        'titles': titles,
        'seniority_bands': seniorityBands,
        'remote_preference': remotePreference,
        'countries': countries,
        'city': ?city,
      },
    );
    return response.data ?? {};
  }

  /// Clears saved Job preferences (204 even if none were stored).
  Future<void> clearPreferences() async {
    await _dio.delete<void>('/api/v1/match-preferences');
  }

  Future<Map<String, dynamic>> jobsForYou() async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/api/v1/jobs-for-you',
    );
    return response.data ?? {};
  }
}

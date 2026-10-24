import 'package:dio/dio.dart';

import '../../../services/api_client.dart';

class ApplicationsService {
  ApplicationsService({ApiClient? client}) : _client = client ?? apiClient;

  final ApiClient _client;

  Dio get _dio => _client.dio;

  Future<List<Map<String, dynamic>>> list() async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/api/v1/applications',
    );
    final items = response.data?['items'];
    if (items is! List) return [];
    return items
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
  }

  Future<Map<String, dynamic>> get(String id) async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/api/v1/applications/$id',
    );
    return response.data ?? {};
  }

  Future<Map<String, dynamic>> markApplied(String id) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/api/v1/applications/$id/mark-applied',
    );
    return response.data ?? {};
  }
}

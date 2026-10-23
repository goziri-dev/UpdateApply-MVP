import 'package:dio/dio.dart';

import '../../../services/api_client.dart';

class TailorService {
  TailorService({ApiClient? client}) : _client = client ?? apiClient;

  final ApiClient _client;

  Dio get _dio => _client.dio;

  /// Live OpenRouter tailor can take a while (embed JD + LLM rewrite).
  static const Duration _connectTimeout = Duration(seconds: 120);
  static const Duration _receiveTimeout = Duration(seconds: 90);

  Future<Map<String, dynamic>> tailor({
    required String jobDescription,
    String? targetRole,
    String? company,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/api/v1/tailor',
      data: {
        'job_description': jobDescription,
        if (targetRole != null && targetRole.trim().isNotEmpty)
          'target_role': targetRole.trim(),
        if (company != null && company.trim().isNotEmpty)
          'company': company.trim(),
      },
      options: Options(
        connectTimeout: _connectTimeout,
        receiveTimeout: _receiveTimeout,
      ),
    );
    return response.data ?? {};
  }
}

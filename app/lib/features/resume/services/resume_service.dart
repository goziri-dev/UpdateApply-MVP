import 'dart:typed_data';

import 'package:dio/dio.dart';

import '../../../services/api_client.dart';

/// Resume HTML preview + PDF export (same server templates as PDF).
class ResumeService {
  ResumeService({ApiClient? client}) : _client = client ?? apiClient;

  final ApiClient _client;

  Dio get _dio => _client.dio;

  static const String defaultTemplateId = 'classic';

  /// Master remade profile as ResumeDocument JSON.
  Future<Map<String, dynamic>> getDocument() async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/api/v1/resume/document',
    );
    return response.data ?? {};
  }

  /// Server-rendered HTML for the master profile (iframe preview).
  Future<String> fetchMasterHtml({
    String templateId = defaultTemplateId,
  }) async {
    final response = await _dio.get<String>(
      '/api/v1/resume/html',
      queryParameters: {'template_id': templateId},
      options: Options(responseType: ResponseType.plain),
    );
    return response.data ?? '';
  }

  /// HTML for an explicit resume map (e.g. tailor result).
  Future<String> fetchHtmlForResume(
    Map<String, dynamic> resume, {
    String templateId = defaultTemplateId,
  }) async {
    final response = await _dio.post<String>(
      '/api/v1/resume/html',
      data: {'template_id': templateId, 'resume': resume},
      options: Options(responseType: ResponseType.plain),
    );
    return response.data ?? '';
  }

  /// Canonical PDF download — same HTML template as preview.
  Future<Uint8List> exportPdf({
    Map<String, dynamic>? resume,
    String templateId = defaultTemplateId,
  }) async {
    final response = await _dio.post<List<int>>(
      '/api/v1/resume/export',
      data: {'template_id': templateId, 'resume': ?resume},
      options: Options(
        responseType: ResponseType.bytes,
        receiveTimeout: const Duration(seconds: 60),
      ),
    );
    final data = response.data;
    if (data == null || data.isEmpty) {
      throw DioException(
        requestOptions: response.requestOptions,
        response: response,
        type: DioExceptionType.badResponse,
        message: 'Empty PDF from server',
      );
    }
    return Uint8List.fromList(data);
  }
}

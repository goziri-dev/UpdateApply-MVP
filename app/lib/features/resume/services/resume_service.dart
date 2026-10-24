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

  /// Persist master ResumeDocument (profile + reindex on server).
  Future<Map<String, dynamic>> putDocument(Map<String, dynamic> resume) async {
    final response = await _dio.put<Map<String, dynamic>>(
      '/api/v1/resume/document',
      data: resume,
    );
    return response.data ?? {};
  }

  /// Agentic propose — returns harness fields without persisting.
  ///
  /// Response shape: `{resume, stub?, detail?, mode, session_id, applied,
  /// confidence?}`.
  static const Duration _editConnectTimeout = Duration(seconds: 120);
  static const Duration _editReceiveTimeout = Duration(seconds: 90);

  Future<Map<String, dynamic>> proposeEdit({
    required Map<String, dynamic> resume,
    required String instruction,
    String mode = 'edit',
    String? sessionId,
    String? priorOutcome,
  }) async {
    final body = <String, dynamic>{
      'resume': resume,
      'instruction': instruction,
      'mode': mode,
      if (sessionId != null && sessionId.isNotEmpty) 'session_id': sessionId,
      if (priorOutcome != null && priorOutcome.isNotEmpty)
        'prior_outcome': priorOutcome,
    };
    final response = await _dio.post<Map<String, dynamic>>(
      '/api/v1/resume/edit',
      data: body,
      options: Options(
        connectTimeout: _editConnectTimeout,
        receiveTimeout: _editReceiveTimeout,
      ),
    );
    return response.data ?? {};
  }

  /// Drop server-side edit session memory (leave screen / reset).
  Future<void> clearEditSession(String sessionId) async {
    if (sessionId.isEmpty) return;
    await _dio.delete('/api/v1/resume/edit/session/$sessionId');
  }

  static const Duration _deepenConnectTimeout = Duration(seconds: 120);
  static const Duration _deepenReceiveTimeout = Duration(seconds: 90);

  /// Start guided or journal deepen for one experience/project (no onboarding gate).
  ///
  /// [mode] is `guided` (novel consultant Qs) or `journal` (freeform dump session).
  Future<Map<String, dynamic>> deepenStart({
    required Map<String, dynamic> resume,
    required String section,
    required int index,
    String mode = 'guided',
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/api/v1/resume/deepen/start',
      data: {
        'resume': resume,
        'section': section,
        'index': index,
        'mode': mode,
      },
      options: Options(
        connectTimeout: _deepenConnectTimeout,
        receiveTimeout: _deepenReceiveTimeout,
      ),
    );
    return response.data ?? {};
  }

  /// Freeform journal dump → optional clarify or ready proposal.
  Future<Map<String, dynamic>> deepenJournal({
    required Map<String, dynamic> resume,
    required String section,
    required int index,
    required String text,
    bool skipClarify = false,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/api/v1/resume/deepen/journal',
      data: {
        'resume': resume,
        'section': section,
        'index': index,
        'text': text,
        'skip_clarify': skipClarify,
      },
      options: Options(
        connectTimeout: _deepenConnectTimeout,
        receiveTimeout: _deepenReceiveTimeout,
      ),
    );
    return response.data ?? {};
  }

  Future<Map<String, dynamic>> deepenTurn({
    required String sessionId,
    required String transcript,
    bool forceDone = false,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/api/v1/resume/deepen/turn',
      data: {
        'session_id': sessionId,
        'transcript': transcript,
        'force_done': forceDone,
      },
    );
    return response.data ?? {};
  }

  /// Item-level rewrite from deepen transcripts (no persist).
  Future<Map<String, dynamic>> deepenPropose({
    required String sessionId,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/api/v1/resume/deepen/propose',
      data: {'session_id': sessionId},
      options: Options(
        connectTimeout: _deepenConnectTimeout,
        receiveTimeout: _deepenReceiveTimeout,
      ),
    );
    return response.data ?? {};
  }

  Future<void> clearDeepenSession(String sessionId) async {
    if (sessionId.isEmpty) return;
    await _dio.delete('/api/v1/resume/deepen/$sessionId');
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

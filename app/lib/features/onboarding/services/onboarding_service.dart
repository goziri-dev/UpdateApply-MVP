import 'dart:typed_data';

import 'package:dio/dio.dart';

import '../../../services/api_client.dart';

class OnboardingService {
  OnboardingService({ApiClient? client}) : _client = client ?? apiClient;

  final ApiClient _client;

  Dio get _dio => _client.dio;

  Future<Map<String, dynamic>> status() async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/api/v1/onboarding/status',
    );
    return response.data ?? {};
  }

  Future<Map<String, dynamic>> uploadPdf({
    required String filename,
    required Uint8List bytes,
  }) async {
    final form = FormData.fromMap({
      'file': MultipartFile.fromBytes(bytes, filename: filename),
    });
    final response = await _dio.post<Map<String, dynamic>>(
      '/api/v1/onboarding/upload',
      data: form,
      options: Options(contentType: 'multipart/form-data'),
    );
    return response.data ?? {};
  }

  Future<Map<String, dynamic>> parse() async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/api/v1/onboarding/parse',
    );
    return response.data ?? {};
  }

  Future<Map<String, dynamic>> interviewState() async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/api/v1/onboarding/interview',
    );
    return response.data ?? {};
  }

  Future<Map<String, dynamic>> interviewTurn({
    required String itemId,
    required String transcript,
    bool forceDone = false,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/api/v1/onboarding/interview/turn',
      data: {
        'item_id': itemId,
        'transcript': transcript,
        'force_done': forceDone,
      },
    );
    return response.data ?? {};
  }

  Future<Map<String, dynamic>> getProfile() async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/api/v1/onboarding/profile',
    );
    return response.data ?? {};
  }

  Future<Map<String, dynamic>> updateProfile(Map<String, dynamic> data) async {
    final response = await _dio.put<Map<String, dynamic>>(
      '/api/v1/onboarding/profile',
      data: {'data': data},
    );
    return response.data ?? {};
  }

  Future<Map<String, dynamic>> complete() async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/api/v1/onboarding/complete',
    );
    return response.data ?? {};
  }
}

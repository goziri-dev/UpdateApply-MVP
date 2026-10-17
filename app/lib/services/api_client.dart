import 'package:dio/dio.dart';

/// Base URL for local API. Prefer reading from env at build time later.
const String kApiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://localhost:8000',
);

class ApiClient {
  ApiClient({Dio? dio})
    : dio =
          dio ??
          Dio(
            BaseOptions(
              baseUrl: kApiBaseUrl,
              connectTimeout: const Duration(seconds: 10),
              receiveTimeout: const Duration(seconds: 30),
              headers: {'Accept': 'application/json'},
            ),
          );

  final Dio dio;

  Future<Map<String, dynamic>> health() async {
    final response = await dio.get<Map<String, dynamic>>('/health');
    return response.data ?? {};
  }
}

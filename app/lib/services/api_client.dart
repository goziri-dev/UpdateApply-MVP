import 'package:dio/dio.dart';

import '../core/config/app_env.dart';
import '../features/auth/services/auth_service.dart';

class ApiClient {
  ApiClient({Dio? dio, AuthService? authService})
    : _auth = authService ?? AuthService(),
      dio =
          dio ??
          Dio(
            BaseOptions(
              baseUrl: AppEnv.apiBaseUrl,
              connectTimeout: const Duration(seconds: 10),
              receiveTimeout: const Duration(seconds: 30),
              headers: {'Accept': 'application/json'},
            ),
          ) {
    this.dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          final token = _auth.accessToken;
          if (token != null && token.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          return handler.next(options);
        },
      ),
    );
  }

  final Dio dio;
  final AuthService _auth;

  Future<Map<String, dynamic>> health() async {
    final response = await dio.get<Map<String, dynamic>>('/health');
    return response.data ?? {};
  }
}

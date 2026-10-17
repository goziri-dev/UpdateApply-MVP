import 'package:supabase_flutter/supabase_flutter.dart';

import '../../../core/config/app_env.dart';
import '../services/auth_service.dart';

/// Feature-level auth access for screens and the API client.
///
/// OAuth helpers: Google, GitHub, Notion (UI order matches `prototypes/auth/`).
class AuthRepository {
  AuthRepository({AuthService? authService})
    : _auth = authService ?? AuthService();

  final AuthService _auth;

  AuthService get service => _auth;

  bool get isSignedIn =>
      AppEnv.supabaseConfigured && _auth.currentSession != null;

  String? get bearerToken => _auth.accessToken;

  Stream<AuthState> authStateChanges() {
    if (!AppEnv.supabaseConfigured) {
      return const Stream.empty();
    }
    return _auth.authStateChanges();
  }

  Future<AuthResponse> signInWithEmail({
    required String email,
    required String password,
  }) {
    return _auth.signInWithPassword(email: email, password: password);
  }

  Future<AuthResponse> signUpWithEmail({
    required String email,
    required String password,
  }) {
    return _auth.signUp(email: email, password: password);
  }

  Future<void> sendPasswordResetEmail(String email) {
    return _auth.resetPasswordForEmail(email);
  }

  Future<bool> continueWithGoogle() =>
      _auth.signInWithOAuth(AuthOAuthProvider.google);

  Future<bool> continueWithGitHub() =>
      _auth.signInWithOAuth(AuthOAuthProvider.github);

  Future<bool> continueWithNotion() =>
      _auth.signInWithOAuth(AuthOAuthProvider.notion);

  Future<bool> linkGoogle() => _auth.linkIdentity(AuthOAuthProvider.google);

  Future<bool> linkGitHub() => _auth.linkIdentity(AuthOAuthProvider.github);

  Future<bool> linkNotion() => _auth.linkIdentity(AuthOAuthProvider.notion);

  Future<void> signOut() => _auth.signOut();
}

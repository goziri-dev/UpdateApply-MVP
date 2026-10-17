import '../services/auth_service.dart';

/// Feature-level auth access. Screens will call this after prototype approval.
///
/// v1 OAuth helpers are Google-only.
class AuthRepository {
  AuthRepository({AuthService? authService})
    : _auth = authService ?? AuthService();

  final AuthService _auth;

  AuthService get service => _auth;

  bool get isSignedIn => _auth.currentSession != null;

  String? get bearerToken => _auth.accessToken;

  Future<bool> continueWithGoogle() => _auth.signInWithGoogle();

  Future<bool> linkGoogle() => _auth.linkGoogle();

  Future<void> signOut() => _auth.signOut();
}

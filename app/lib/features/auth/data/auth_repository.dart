import '../services/auth_service.dart';

/// Feature-level auth access. Screens will call this after prototype approval.
///
/// OAuth helpers: Google, GitHub, Notion (UI order matches `prototypes/auth/`).
class AuthRepository {
  AuthRepository({AuthService? authService})
    : _auth = authService ?? AuthService();

  final AuthService _auth;

  AuthService get service => _auth;

  bool get isSignedIn => _auth.currentSession != null;

  String? get bearerToken => _auth.accessToken;

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

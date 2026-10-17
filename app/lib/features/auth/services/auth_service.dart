import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../../core/config/app_env.dart';
import 'supabase_bootstrap.dart';

/// Thin wrapper around supabase_flutter auth. UI screens come after prototype OK.
///
/// v1 OAuth surface is Google-only (see `prototypes/auth/`).
class AuthService {
  AuthService({this._client});

  final SupabaseClient? _client;

  SupabaseClient get client {
    final c = _client ?? (AppEnv.supabaseConfigured ? supabase : null);
    if (c == null) {
      throw StateError(
        'Supabase is not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY.',
      );
    }
    return c;
  }

  Session? get currentSession =>
      AppEnv.supabaseConfigured ? client.auth.currentSession : null;

  User? get currentUser =>
      AppEnv.supabaseConfigured ? client.auth.currentUser : null;

  Stream<AuthState> authStateChanges() => client.auth.onAuthStateChange;

  String? get accessToken => currentSession?.accessToken;

  /// Redirect used after OAuth. Web uses origin unless overridden.
  String? get oauthRedirectTo {
    if (AppEnv.supabaseAuthRedirectUrl.isNotEmpty) {
      return AppEnv.supabaseAuthRedirectUrl;
    }
    if (kIsWeb) {
      return Uri.base.origin;
    }
    return 'io.updateapply.app://login-callback/';
  }

  Future<bool> signInWithGoogle() async {
    return client.auth.signInWithOAuth(
      OAuthProvider.google,
      redirectTo: oauthRedirectTo,
      authScreenLaunchMode: kIsWeb
          ? LaunchMode.platformDefault
          : LaunchMode.externalApplication,
    );
  }

  Future<bool> linkGoogle() {
    return client.auth.linkIdentity(
      OAuthProvider.google,
      redirectTo: oauthRedirectTo,
      authScreenLaunchMode: kIsWeb
          ? LaunchMode.platformDefault
          : LaunchMode.externalApplication,
    );
  }

  Future<void> signOut() => client.auth.signOut();
}

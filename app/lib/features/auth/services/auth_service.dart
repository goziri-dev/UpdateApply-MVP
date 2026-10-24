import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../../core/config/app_env.dart';
import 'supabase_bootstrap.dart';

/// OAuth providers enabled for UpdateApply (Dashboard → Authentication → Providers).
/// UI order: Google → GitHub → Notion (see `prototypes/auth/`).
enum AuthOAuthProvider { google, github, notion }

extension on AuthOAuthProvider {
  OAuthProvider get gotrue {
    return switch (this) {
      AuthOAuthProvider.google => OAuthProvider.google,
      AuthOAuthProvider.github => OAuthProvider.github,
      AuthOAuthProvider.notion => OAuthProvider.notion,
    };
  }
}

/// Thin wrapper around supabase_flutter auth.
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

  /// Redirect used after OAuth / email links. Web uses origin unless overridden.
  ///
  /// Must be allow-listed in Supabase Dashboard → Authentication → URL
  /// Configuration. On web this should be the **same origin** as the app so
  /// PKCE returns into one tab (`detectSessionInUri` + GoRouter).
  String? get oauthRedirectTo {
    if (AppEnv.supabaseAuthRedirectUrl.isNotEmpty) {
      return AppEnv.supabaseAuthRedirectUrl;
    }
    if (kIsWeb) {
      return Uri.base.origin;
    }
    return 'io.updateapply.app://login-callback/';
  }

  Future<AuthResponse> signInWithPassword({
    required String email,
    required String password,
  }) {
    return client.auth.signInWithPassword(email: email, password: password);
  }

  Future<AuthResponse> signUp({
    required String email,
    required String password,
  }) {
    return client.auth.signUp(
      email: email,
      password: password,
      emailRedirectTo: oauthRedirectTo,
    );
  }

  Future<void> resetPasswordForEmail(String email) {
    return client.auth.resetPasswordForEmail(
      email,
      redirectTo: oauthRedirectTo,
    );
  }

  /// Starts OAuth. On web, supabase_flutter launches with `webOnlyWindowName:
  /// '_self'` (same-tab redirect). Do **not** use `_blank` — that leaves a
  /// duplicate UpdateApply tab after the callback.
  ///
  /// Debug note: same-tab navigation briefly disconnects DWDS; after the IdP
  /// returns to this origin the app reloads, PKCE completes, and routing
  /// continues from `/boot` as usual.
  Future<bool> signInWithOAuth(AuthOAuthProvider provider) {
    return client.auth.signInWithOAuth(
      provider.gotrue,
      redirectTo: oauthRedirectTo,
      authScreenLaunchMode: kIsWeb
          ? LaunchMode.platformDefault
          : LaunchMode.externalApplication,
    );
  }

  Future<bool> linkIdentity(AuthOAuthProvider provider) {
    return client.auth.linkIdentity(
      provider.gotrue,
      redirectTo: oauthRedirectTo,
      authScreenLaunchMode: kIsWeb
          ? LaunchMode.platformDefault
          : LaunchMode.externalApplication,
    );
  }

  Future<void> signOut() => client.auth.signOut();
}

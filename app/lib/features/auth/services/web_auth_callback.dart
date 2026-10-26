import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../../core/config/app_env.dart';
import 'supabase_bootstrap.dart';
import 'web_auth_callback_uri_stub.dart'
    if (dart.library.js_interop) 'web_auth_callback_uri_web.dart';

/// True when [uri] carries Supabase auth callback params (PKCE or implicit).
bool uriHasAuthCallbackParams(Uri uri) {
  final fragmentParameters = Uri.splitQueryString(uri.fragment);
  bool has(String key) =>
      uri.queryParameters.containsKey(key) ||
      fragmentParameters.containsKey(key);

  return has('code') ||
      has('access_token') ||
      has('error') ||
      has('error_code') ||
      has('error_description');
}

/// Ensures a web OAuth / magic-link return finishes exchanging before routing.
///
/// `Supabase.initialize` already runs [detectSessionInUri], but hash URL
/// strategy and cold-start timing can leave `currentSession` null while the
/// router treats the user as signed out and sends them to `/auth`. Call this
/// after initialize and keep [authHydrated] false until it completes.
Future<void> recoverWebAuthCallbackSession() async {
  if (!kIsWeb || !AppEnv.supabaseConfigured) return;

  // Prefer the live browser href (query before `#`) over Flutter's Uri.base,
  // which can disagree under hash routing during the OAuth return.
  final uri = currentAuthCallbackUri();
  if (!uriHasAuthCallbackParams(uri)) return;

  if (supabase.auth.currentSession != null) {
    debugPrint('Auth callback URL present; session already restored.');
    return;
  }

  // initialize() kicks off recoverSession without awaiting it; give a brief
  // window for storage restore before re-attempting the URL exchange.
  for (var i = 0; i < 20 && supabase.auth.currentSession == null; i++) {
    await Future<void>.delayed(const Duration(milliseconds: 25));
  }
  if (supabase.auth.currentSession != null) return;

  try {
    await supabase.auth.getSessionFromUrl(uri);
    debugPrint('Auth callback session recovered from URL.');
  } on AuthException catch (error, stackTrace) {
    // Code may already have been exchanged during initialize — only log.
    if (supabase.auth.currentSession != null) return;
    debugPrint('Auth callback exchange failed: $error\n$stackTrace');
  } on Object catch (error, stackTrace) {
    if (supabase.auth.currentSession != null) return;
    debugPrint('Auth callback exchange failed: $error\n$stackTrace');
  }
}

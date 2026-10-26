import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../../core/config/app_env.dart';
import 'web_auth_callback.dart';

/// Initializes the Supabase client when URL + anon/publishable key are present.
///
/// After this returns, callers should [markAuthHydrated] so GoRouter can leave
/// `/boot`. Web OAuth `?code=` recovery runs here before that mark.
Future<void> bootstrapSupabase() async {
  if (!AppEnv.supabaseConfigured) {
    debugPrint(
      'Supabase skipped: set SUPABASE_URL and SUPABASE_ANON_KEY '
      '(flutter run --dart-define-from-file=.env).',
    );
    return;
  }

  await Supabase.initialize(
    url: AppEnv.supabaseUrl,
    publishableKey: AppEnv.supabaseAnonKey,
    authOptions: const FlutterAuthClientOptions(
      authFlowType: AuthFlowType.pkce,
    ),
  );
  await recoverWebAuthCallbackSession();
}

SupabaseClient get supabase => Supabase.instance.client;

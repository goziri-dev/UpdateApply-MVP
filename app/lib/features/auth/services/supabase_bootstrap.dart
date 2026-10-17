import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../../core/config/app_env.dart';

/// Initializes the Supabase client when URL + anon/publishable key are present.
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
}

SupabaseClient get supabase => Supabase.instance.client;

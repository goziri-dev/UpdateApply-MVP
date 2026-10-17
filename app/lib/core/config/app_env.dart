/// Build-time / define-from-file configuration for the Flutter client.
///
/// Load values with:
/// `flutter run --dart-define-from-file=.env`
///
/// Never put the Supabase **service_role** key here — anon/publishable only.
class AppEnv {
  const AppEnv._();

  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

  static const String supabaseUrl = String.fromEnvironment('SUPABASE_URL');

  /// Legacy anon key or new publishable key — both work with supabase_flutter.
  static const String supabaseAnonKey = String.fromEnvironment(
    'SUPABASE_ANON_KEY',
  );

  /// Optional override for OAuth redirect. On web, defaults to current origin.
  /// Example native: `io.updateapply.app://login-callback/`
  static const String supabaseAuthRedirectUrl = String.fromEnvironment(
    'SUPABASE_AUTH_REDIRECT_URL',
  );

  static bool get supabaseConfigured =>
      supabaseUrl.isNotEmpty && supabaseAnonKey.isNotEmpty;
}

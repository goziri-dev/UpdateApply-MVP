import 'package:aptabase_flutter/aptabase_flutter.dart';
import 'package:flutter/foundation.dart';

import '../config/app_env.dart';

/// Thin Aptabase wrapper. No-ops when [AppEnv.aptabaseAppKey] is empty.
///
/// Privacy: never pass resume text, emails, names, or other PII in [props].
/// Aptabase allows only `String` / `num` property values (no bools).
class Analytics {
  Analytics._();

  static bool _ready = false;
  static bool _allowlistSignupTracked = false;

  static bool get isEnabled => _ready;

  /// Init after [WidgetsFlutterBinding.ensureInitialized].
  ///
  /// EU keys (`A-EU-*`) resolve the host from the key prefix — do **not** set
  /// [InitOptions.host] (that is only for self-hosted `A-SH-*` keys).
  static Future<void> init() async {
    final key = AppEnv.aptabaseAppKey.trim();
    if (key.isEmpty) {
      if (kDebugMode) {
        debugPrint(
          'Analytics: APTABASE_APP_KEY unset — product analytics disabled.',
        );
      }
      _ready = false;
      return;
    }

    try {
      await Aptabase.init(
        key,
        kDebugMode
            ? const InitOptions(printDebugMessages: true)
            : const InitOptions(),
      );
      _ready = true;
      track('app_started');
    } on Object catch (error, stackTrace) {
      _ready = false;
      debugPrint('Analytics: Aptabase.init failed: $error\n$stackTrace');
    }
  }

  static void track(String name, [Map<String, Object>? props]) {
    if (!_ready) return;
    try {
      if (props == null || props.isEmpty) {
        Aptabase.instance.trackEvent(name);
      } else {
        Aptabase.instance.trackEvent(name, props);
      }
    } on Object catch (error) {
      debugPrint('Analytics: trackEvent($name) failed: $error');
    }
  }

  /// Funnel entry for private beta: first allowlist pass this app session.
  ///
  /// Covers email + OAuth once `/auth/me` reports allowlisted. Session-deduped
  /// so cold starts do not spam; Aptabase funnels still use unique users.
  static void trackSignupCompleted({required String method}) {
    if (_allowlistSignupTracked) return;
    _allowlistSignupTracked = true;
    track('signup_completed', {'method': method});
  }

  static void trackResumeUploaded({required int sizeBytes}) {
    final sizeKb = (sizeBytes / 1024).round();
    track('resume_uploaded', {'size_kb': sizeKb});
  }

  static void trackTailorSucceeded({
    required bool stub,
    required bool hasPosting,
  }) {
    track('tailor_succeeded', {
      'stub': stub ? 1 : 0,
      'has_posting': hasPosting ? 1 : 0,
    });
  }

  static void trackPdfDownloaded({required String kind}) {
    track('pdf_downloaded', {'kind': kind});
  }
}

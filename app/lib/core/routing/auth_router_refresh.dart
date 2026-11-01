import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../features/auth/data/auth_repository.dart';
import '../../features/auth/state/allowlist_state.dart';
import '../../features/auth/state/auth_state.dart';
import '../../features/onboarding/state/onboarding_state.dart';
import '../../services/api_client.dart';
import '../analytics/analytics.dart';

/// Notifies [GoRouter] when Supabase auth session (or onboarding gate) changes.
class AuthRouterRefresh extends ChangeNotifier {
  AuthRouterRefresh([AuthRepository? repository]) {
    final auth = repository ?? authRepository;
    // Supabase may emit from JS/interop outside the scoped_deps zone; bind
    // so gate writes hit the same signals GoRouter redirects read.
    final zone = Zone.current;
    _subscription = auth.authStateChanges().listen(
      zone.bindUnaryCallback((_) {
        unawaited(_syncGateAndNotify());
      }),
    );
    unawaited(_syncGateAndNotify());
  }

  StreamSubscription<AuthState>? _subscription;
  int _syncGeneration = 0;

  static const _unreachableMessage = "Can't reach the server.";

  Future<void> retryGateSync() => _syncGateAndNotify();

  /// Map `/auth/me` failures to a gate message (avoid treating 503/CORS as silence).
  static String _gateSyncFailureMessage(Object error) {
    if (error is DioException) {
      final status = error.response?.statusCode;
      final data = error.response?.data;
      if (data is Map && data['detail'] is String) {
        final detail = (data['detail'] as String).trim();
        if (detail.isNotEmpty) {
          if (status == 503) {
            return 'API auth is not configured locally. $detail';
          }
          return detail;
        }
      }
      switch (error.type) {
        case DioExceptionType.connectionTimeout:
        case DioExceptionType.sendTimeout:
        case DioExceptionType.receiveTimeout:
        case DioExceptionType.connectionError:
          return _unreachableMessage;
        default:
          break;
      }
      if (status != null) {
        return "Can't reach the server (HTTP $status).";
      }
    }
    return _unreachableMessage;
  }

  Future<void> _syncGateAndNotify() async {
    final generation = ++_syncGeneration;

    // ReplaySubject may emit initialSession(null) before signedIn; never treat
    // that as a final signed-out redirect until bootstrap marked auth ready.
    if (!authHydrated.value) {
      notifyListeners();
      return;
    }

    if (!authRepository.isSignedIn) {
      onboardingGate.value = OnboardingGate.unknown;
      applyOnboardingStep(null);
      allowlistGate.value = AllowlistGate.unknown;
      onboardingGateSyncing.value = false;
      onboardingGateSyncError.value = null;
      if (generation == _syncGeneration) notifyListeners();
      return;
    }

    onboardingGateSyncing.value = true;
    onboardingGateSyncError.value = null;
    if (generation == _syncGeneration) notifyListeners();

    try {
      final me = await apiClient.authMe();
      if (generation != _syncGeneration) return;
      allowlistGate.value = allowlistFromMe(me);
      if (allowlistGate.value == AllowlistGate.allowed) {
        // Funnel entry for private beta (covers email + OAuth once allowlisted).
        Analytics.trackSignupCompleted(method: 'allowlist');
      }
      if (allowlistGate.value == AllowlistGate.denied) {
        onboardingGate.value = OnboardingGate.unknown;
        applyOnboardingStep(null);
        onboardingGateSyncError.value = null;
      } else {
        _applyStatus(me['onboarding_status']);
        // Prefer /onboarding/status so resume step survives boot redirects.
        try {
          final st = await onboardingService.status();
          if (generation != _syncGeneration) return;
          if (st['status'] != null) {
            _applyStatus(st['status']);
          }
          applyOnboardingStep(st['step']);
        } on Object {
          // Keep /auth/me status; step stays previous/null until next sync.
        }
      }
    } on Object catch (error) {
      // Onboarding status API is allowlist-gated; do not use it as a
      // fallback for /auth/me (would 403 for denied users).
      if (generation != _syncGeneration) return;
      if (allowlistGate.value == AllowlistGate.unknown) {
        onboardingGateSyncError.value = _gateSyncFailureMessage(error);
      }
    } finally {
      if (generation == _syncGeneration) {
        onboardingGateSyncing.value = false;
      }
    }
    if (generation == _syncGeneration) notifyListeners();
  }

  void _applyStatus(Object? raw) {
    final status = raw is String ? raw : raw?.toString();
    final gate = gateFromStatus(status);
    onboardingGate.value = gate;
    if (gate == OnboardingGate.unknown) {
      onboardingGateSyncError.value =
          'Unexpected profile status${status == null ? '' : ' "$status"'}. '
          'Retry, or sign out and back in.';
    } else {
      onboardingGateSyncError.value = null;
    }
  }

  void notifyGateChanged() => notifyListeners();

  @override
  void dispose() {
    unawaited(_subscription?.cancel());
    super.dispose();
  }
}

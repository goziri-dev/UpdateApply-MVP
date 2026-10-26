import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../features/auth/data/auth_repository.dart';
import '../../features/auth/state/allowlist_state.dart';
import '../../features/auth/state/auth_state.dart';
import '../../features/onboarding/state/onboarding_state.dart';
import '../../services/api_client.dart';

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
      if (allowlistGate.value == AllowlistGate.denied) {
        onboardingGate.value = OnboardingGate.unknown;
        onboardingGateSyncError.value = null;
      } else {
        _applyStatus(me['onboarding_status']);
      }
    } on Object {
      // Onboarding status API is allowlist-gated; do not use it as a
      // fallback for /auth/me (would 403 for denied users).
      if (generation != _syncGeneration) return;
      if (allowlistGate.value == AllowlistGate.unknown) {
        onboardingGateSyncError.value = _unreachableMessage;
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

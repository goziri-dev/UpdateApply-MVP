import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../features/auth/data/auth_repository.dart';
import '../../features/auth/state/auth_state.dart';
import '../../features/onboarding/state/onboarding_state.dart';
import '../../services/api_client.dart';

/// Notifies [GoRouter] when Supabase auth session (or onboarding gate) changes.
class AuthRouterRefresh extends ChangeNotifier {
  AuthRouterRefresh([AuthRepository? repository]) {
    final auth = repository ?? authRepository;
    _subscription = auth.authStateChanges().listen((_) {
      unawaited(_syncGateAndNotify());
    });
    unawaited(_syncGateAndNotify());
  }

  StreamSubscription<AuthState>? _subscription;

  static const _unreachableMessage =
      "Can't reach the server. Check that the API is running, then retry.";

  Future<void> retryGateSync() => _syncGateAndNotify();

  Future<void> _syncGateAndNotify() async {
    if (!authRepository.isSignedIn) {
      onboardingGate.value = OnboardingGate.unknown;
      onboardingGateSyncing.value = false;
      onboardingGateSyncError.value = null;
      notifyListeners();
      return;
    }

    onboardingGateSyncing.value = true;
    onboardingGateSyncError.value = null;
    notifyListeners();

    try {
      final me = await apiClient.authMe();
      onboardingGate.value = gateFromStatus(me['onboarding_status'] as String?);
      onboardingGateSyncError.value = null;
    } on Object {
      try {
        final status = await onboardingService.status();
        onboardingGate.value = gateFromStatus(status['status'] as String?);
        onboardingGateSyncError.value = null;
      } on Object {
        if (onboardingGate.value == OnboardingGate.unknown) {
          onboardingGateSyncError.value = _unreachableMessage;
        }
      }
    } finally {
      onboardingGateSyncing.value = false;
    }
    notifyListeners();
  }

  void notifyGateChanged() => notifyListeners();

  @override
  void dispose() {
    unawaited(_subscription?.cancel());
    super.dispose();
  }
}

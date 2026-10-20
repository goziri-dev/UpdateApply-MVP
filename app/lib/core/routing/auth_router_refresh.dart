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

  Future<void> _syncGateAndNotify() async {
    if (!authRepository.isSignedIn) {
      onboardingGate.value = OnboardingGate.unknown;
      notifyListeners();
      return;
    }
    try {
      final me = await apiClient.authMe();
      onboardingGate.value = gateFromStatus(me['onboarding_status'] as String?);
    } on Object {
      try {
        await refreshOnboardingGate();
      } on Object {
        // Leave unknown; redirect stays conservative.
      }
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

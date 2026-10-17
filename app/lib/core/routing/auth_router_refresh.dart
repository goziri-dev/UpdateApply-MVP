import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../features/auth/data/auth_repository.dart';
import '../../features/auth/state/auth_state.dart';

/// Notifies [GoRouter] when Supabase auth session changes.
class AuthRouterRefresh extends ChangeNotifier {
  AuthRouterRefresh([AuthRepository? repository]) {
    final auth = repository ?? authRepository;
    _subscription = auth.authStateChanges().listen((_) {
      notifyListeners();
    });
  }

  StreamSubscription<AuthState>? _subscription;

  @override
  void dispose() {
    unawaited(_subscription?.cancel());
    super.dispose();
  }
}

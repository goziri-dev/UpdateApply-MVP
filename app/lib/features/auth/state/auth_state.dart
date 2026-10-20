import 'package:scoped_deps/scoped_deps.dart';
import 'package:signals/signals.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../../core/config/app_env.dart';
import '../data/auth_repository.dart';
import '../services/auth_service.dart';

/// Which control is currently busy (matches prototype loading targets).
enum AuthBusyTarget { idle, email, google, github, notion, reset }

final authRepositoryRef = create(AuthRepository.new);

final authBusyRef = create(() => signal(AuthBusyTarget.idle));

final authErrorRef = create(() => signal<String?>(null));

final authNoticeRef = create(() => signal<String?>(null));

// Hot reload recreates ScopedRef keys without re-running main()/runScoped.
// Fallbacks keep getters working until a full hot restart.
AuthRepository? _authRepositoryFallback;
Signal<AuthBusyTarget>? _authBusyFallback;
Signal<String?>? _authErrorFallback;
Signal<String?>? _authNoticeFallback;

AuthRepository get authRepository => read(
  authRepositoryRef,
  orElse: () => _authRepositoryFallback ??= AuthRepository(),
);

Signal<AuthBusyTarget> get authBusy => read(
  authBusyRef,
  orElse: () => _authBusyFallback ??= signal(AuthBusyTarget.idle),
);

Signal<String?> get authError => read(
  authErrorRef,
  orElse: () => _authErrorFallback ??= signal<String?>(null),
);

Signal<String?> get authNotice => read(
  authNoticeRef,
  orElse: () => _authNoticeFallback ??= signal<String?>(null),
);

bool get isAuthBusy => authBusy.value != AuthBusyTarget.idle;

void clearAuthFeedback() {
  authError.value = null;
  authNotice.value = null;
}

void setAuthError(String? message) {
  authNotice.value = null;
  authError.value = message;
}

void setAuthNotice(String? message) {
  authError.value = null;
  authNotice.value = message;
}

String mapAuthError(Object error) {
  if (error is AuthException) {
    final message = error.message.trim();
    if (message.isNotEmpty) return message;
  }
  if (error is StateError) {
    return error.message;
  }
  return 'Something went wrong. Check your details or try another provider.';
}

Future<T?> runAuthAction<T>({
  required AuthBusyTarget target,
  required Future<T> Function() action,
  String? successNotice,
}) async {
  if (!AppEnv.supabaseConfigured) {
    setAuthError(
      'Supabase is not configured. Pass SUPABASE_URL and SUPABASE_ANON_KEY '
      'via --dart-define-from-file=.env.',
    );
    return null;
  }
  if (isAuthBusy) return null;

  clearAuthFeedback();
  authBusy.value = target;
  try {
    final result = await action();
    if (successNotice != null) {
      setAuthNotice(successNotice);
    }
    return result;
  } on Object catch (error) {
    setAuthError(mapAuthError(error));
    return null;
  } finally {
    authBusy.value = AuthBusyTarget.idle;
  }
}

Future<void> signInWithEmail({
  required String email,
  required String password,
}) {
  return runAuthAction(
    target: AuthBusyTarget.email,
    action: () =>
        authRepository.signInWithEmail(email: email, password: password),
  );
}

Future<void> signUpWithEmail({
  required String email,
  required String password,
}) {
  return runAuthAction(
    target: AuthBusyTarget.email,
    action: () async {
      final response = await authRepository.signUpWithEmail(
        email: email,
        password: password,
      );
      if (response.session == null) {
        setAuthNotice(
          'Check your email to confirm your account, then sign in.',
        );
      }
    },
  );
}

Future<void> sendPasswordReset({required String email}) {
  return runAuthAction(
    target: AuthBusyTarget.reset,
    action: () => authRepository.sendPasswordResetEmail(email),
    successNotice: 'Reset link sent. Check your email.',
  );
}

Future<void> continueWithOAuth(AuthOAuthProvider provider) {
  final target = switch (provider) {
    AuthOAuthProvider.google => AuthBusyTarget.google,
    AuthOAuthProvider.github => AuthBusyTarget.github,
    AuthOAuthProvider.notion => AuthBusyTarget.notion,
  };
  return runAuthAction(
    target: target,
    action: () async {
      final launched = switch (provider) {
        AuthOAuthProvider.google => await authRepository.continueWithGoogle(),
        AuthOAuthProvider.github => await authRepository.continueWithGitHub(),
        AuthOAuthProvider.notion => await authRepository.continueWithNotion(),
      };
      if (!launched) {
        throw StateError(
          'Could not open the provider. Try again or use email.',
        );
      }
    },
  );
}

Future<void> signOut() => authRepository.signOut();

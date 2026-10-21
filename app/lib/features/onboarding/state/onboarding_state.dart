import 'package:scoped_deps/scoped_deps.dart';
import 'package:signals/signals.dart';

import '../services/onboarding_service.dart';

/// Mirrors backend ``user.onboarding_status``.
///
/// [unknown] means status has not been loaded yet (or the API is unreachable).
/// Routers must not treat unknown as "needs onboarding."
enum OnboardingGate { unknown, notStarted, inProgress, complete }

final onboardingServiceRef = create(OnboardingService.new);

final onboardingGateRef = create(() => signal(OnboardingGate.unknown));
final onboardingGateSyncingRef = create(() => signal(false));
final onboardingGateSyncErrorRef = create(() => signal<String?>(null));
final onboardingBusyRef = create(() => signal(false));
final onboardingErrorRef = create(() => signal<String?>(null));
final onboardingInfoRef = create(() => signal<String?>(null));

OnboardingService? _serviceFallback;
Signal<OnboardingGate>? _gateFallback;
Signal<bool>? _gateSyncingFallback;
Signal<String?>? _gateSyncErrorFallback;
Signal<bool>? _busyFallback;
Signal<String?>? _errorFallback;
Signal<String?>? _infoFallback;

OnboardingService get onboardingService => read(
  onboardingServiceRef,
  orElse: () => _serviceFallback ??= OnboardingService(),
);

Signal<OnboardingGate> get onboardingGate => read(
  onboardingGateRef,
  orElse: () => _gateFallback ??= signal(OnboardingGate.unknown),
);

Signal<bool> get onboardingGateSyncing => read(
  onboardingGateSyncingRef,
  orElse: () => _gateSyncingFallback ??= signal(false),
);

Signal<String?> get onboardingGateSyncError => read(
  onboardingGateSyncErrorRef,
  orElse: () => _gateSyncErrorFallback ??= signal<String?>(null),
);

Signal<bool> get onboardingBusy =>
    read(onboardingBusyRef, orElse: () => _busyFallback ??= signal(false));

Signal<String?> get onboardingError => read(
  onboardingErrorRef,
  orElse: () => _errorFallback ??= signal<String?>(null),
);

Signal<String?> get onboardingInfo => read(
  onboardingInfoRef,
  orElse: () => _infoFallback ??= signal<String?>(null),
);

OnboardingGate gateFromStatus(String? status) {
  return switch (status) {
    'complete' => OnboardingGate.complete,
    'in_progress' => OnboardingGate.inProgress,
    'not_started' => OnboardingGate.notStarted,
    _ => OnboardingGate.unknown,
  };
}

void setOnboardingError(String? message) {
  onboardingError.value = message;
  if (message != null) onboardingInfo.value = null;
}

void setOnboardingInfo(String? message) {
  onboardingInfo.value = message;
  if (message != null) onboardingError.value = null;
}

void clearOnboardingFeedback() {
  onboardingError.value = null;
  onboardingInfo.value = null;
}

Future<void> refreshOnboardingGate({String? statusHint}) async {
  if (statusHint != null) {
    onboardingGate.value = gateFromStatus(statusHint);
    onboardingGateSyncError.value = null;
    onboardingGateSyncing.value = false;
    return;
  }
  onboardingGateSyncing.value = true;
  onboardingGateSyncError.value = null;
  try {
    final me = await onboardingService.status();
    onboardingGate.value = gateFromStatus(me['status'] as String?);
    onboardingGateSyncError.value = null;
  } on Object {
    // Keep last known gate if we already resolved one; otherwise stay unknown.
    if (onboardingGate.value == OnboardingGate.unknown) {
      onboardingGateSyncError.value =
          "Can't reach the server. Check that the API is running, then retry.";
    }
  } finally {
    onboardingGateSyncing.value = false;
  }
}

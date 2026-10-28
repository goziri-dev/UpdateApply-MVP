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
final onboardingStepRef = create(() => signal<String?>(null));
final onboardingGateSyncingRef = create(() => signal(false));
final onboardingGateSyncErrorRef = create(() => signal<String?>(null));
final onboardingBusyRef = create(() => signal(false));
final onboardingErrorRef = create(() => signal<String?>(null));
final onboardingInfoRef = create(() => signal<String?>(null));

OnboardingService? _serviceFallback;
Signal<OnboardingGate>? _gateFallback;
Signal<String?>? _stepFallback;
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

/// Backend ``_onboarding.step`` (upload | interview | review | ready).
Signal<String?> get onboardingStep => read(
  onboardingStepRef,
  orElse: () => _stepFallback ??= signal<String?>(null),
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

void applyOnboardingStep(Object? raw) {
  if (raw == null) {
    onboardingStep.value = null;
    return;
  }
  final step = raw is String ? raw : raw.toString();
  onboardingStep.value = step.isEmpty ? null : step;
}

/// Where incomplete users should land — never force past progress back to upload.
String onboardingEntryLocation() {
  return switch (onboardingStep.value) {
    'ready' => '/onboarding/reveal',
    'review' => '/onboarding/review',
    'interview' => '/onboarding/interview',
    _ => '/onboarding/upload',
  };
}

int _onboardingStepRank(String? step) {
  return switch (step) {
    'ready' => 4,
    'review' => 3,
    'interview' => 2,
    'upload' => 0,
    _ => 0,
  };
}

int _onboardingPathRank(String location) {
  return switch (location) {
    '/onboarding/reveal' || '/onboarding/ready' => 4,
    '/onboarding/review' => 3,
    '/onboarding/interview' => 2,
    '/onboarding/parsing' => 1,
    '/onboarding/upload' => 0,
    _ => -1,
  };
}

/// If the user is on an earlier onboarding screen than their saved step, advance.
String? onboardingCatchUpLocation(String location) {
  final pathRank = _onboardingPathRank(location);
  if (pathRank < 0) return null;
  final stepRank = _onboardingStepRank(onboardingStep.value);
  if (pathRank >= stepRank) return null;
  return onboardingEntryLocation();
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
    final gate = gateFromStatus(statusHint);
    onboardingGate.value = gate;
    if (gate == OnboardingGate.complete) {
      applyOnboardingStep('ready');
    } else if (gate == OnboardingGate.notStarted) {
      applyOnboardingStep('upload');
    }
    onboardingGateSyncError.value = gate == OnboardingGate.unknown
        ? 'Unexpected profile status "$statusHint".'
        : null;
    onboardingGateSyncing.value = false;
    return;
  }
  onboardingGateSyncing.value = true;
  onboardingGateSyncError.value = null;
  try {
    final me = await onboardingService.status();
    final raw = me['status'];
    final status = raw is String ? raw : raw?.toString();
    final gate = gateFromStatus(status);
    onboardingGate.value = gate;
    applyOnboardingStep(me['step']);
    if (gate == OnboardingGate.unknown) {
      onboardingGateSyncError.value =
          'Unexpected profile status${status == null ? '' : ' "$status"'}. '
          'Retry, or sign out and back in.';
    } else {
      onboardingGateSyncError.value = null;
    }
  } on Object {
    // Keep last known gate if we already resolved one; otherwise stay unknown.
    if (onboardingGate.value == OnboardingGate.unknown) {
      onboardingGateSyncError.value =
          "Can't reach the server. Please try again.";
    }
  } finally {
    onboardingGateSyncing.value = false;
  }
}

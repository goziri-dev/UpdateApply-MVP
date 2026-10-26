import 'package:scoped_deps/scoped_deps.dart';
import 'package:signals/signals.dart';

/// Private-beta allowlist gate from ``GET /api/v1/auth/me`` ``allowlisted``.
///
/// [unknown] until /me returns; [denied] shows the waiting screen; [allowed]
/// continues into onboarding / app.
enum AllowlistGate { unknown, denied, allowed }

final allowlistGateRef = create(() => signal(AllowlistGate.unknown));

Signal<AllowlistGate>? _allowlistFallback;

Signal<AllowlistGate> get allowlistGate => read(
  allowlistGateRef,
  orElse: () => _allowlistFallback ??= signal(AllowlistGate.unknown),
);

AllowlistGate allowlistFromMe(Map<String, dynamic> me) {
  final raw = me['allowlisted'];
  if (raw is bool) {
    return raw ? AllowlistGate.allowed : AllowlistGate.denied;
  }
  // Older API without the field — treat as denied (fail closed for beta).
  return AllowlistGate.denied;
}

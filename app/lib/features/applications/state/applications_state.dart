import 'package:scoped_deps/scoped_deps.dart';
import 'package:signals/signals_flutter.dart';

/// Bumped after a successful tailor so the Applications list reloads.
final applicationsEpochRef = create(() => signal(0));

Signal<int>? _applicationsEpochFallback;

Signal<int> get applicationsEpoch => read(
  applicationsEpochRef,
  orElse: () => _applicationsEpochFallback ??= signal(0),
);

void bumpApplicationsEpoch() {
  applicationsEpoch.value = applicationsEpoch.value + 1;
}

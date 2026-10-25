import 'package:scoped_deps/scoped_deps.dart';
import 'package:signals/signals_flutter.dart';

/// Bumped after a successful master-resume save so Home (and other master
/// previews) refetch HTML.
///
/// Home remounts on tab switch (active-branch shell). Epoch still refreshes
/// previews that stay mounted under a pushed route (e.g. after /resume/edit).
final masterResumeEpochRef = create(() => signal(0));

Signal<int>? _masterResumeEpochFallback;

Signal<int> get masterResumeEpoch => read(
  masterResumeEpochRef,
  orElse: () => _masterResumeEpochFallback ??= signal(0),
);

void bumpMasterResumeEpoch() {
  masterResumeEpoch.value = masterResumeEpoch.value + 1;
}

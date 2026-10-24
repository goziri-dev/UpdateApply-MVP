import 'package:scoped_deps/scoped_deps.dart';
import 'package:signals/signals_flutter.dart';

/// Bumped after a successful master-resume save so Home (and other master
/// previews) refetch HTML.
///
/// Home lives in a [StatefulShellRoute] indexed stack; its [ResumePreview]
/// only loads in initState unless this epoch changes.
final masterResumeEpochRef = create(() => signal(0));

Signal<int>? _masterResumeEpochFallback;

Signal<int> get masterResumeEpoch => read(
  masterResumeEpochRef,
  orElse: () => _masterResumeEpochFallback ??= signal(0),
);

void bumpMasterResumeEpoch() {
  masterResumeEpoch.value = masterResumeEpoch.value + 1;
}

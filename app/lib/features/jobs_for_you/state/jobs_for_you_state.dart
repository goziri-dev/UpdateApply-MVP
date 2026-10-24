import 'package:scoped_deps/scoped_deps.dart';
import 'package:signals/signals_flutter.dart';

/// Bumped after Job preferences save so Jobs For You reloads.
///
/// The Jobs tab lives in a [StatefulShellRoute] indexed stack, so it stays
/// mounted across navigation and would otherwise keep a stale empty_reason.
final jobsForYouEpochRef = create(() => signal(0));

Signal<int>? _jobsForYouEpochFallback;

Signal<int> get jobsForYouEpoch => read(
  jobsForYouEpochRef,
  orElse: () => _jobsForYouEpochFallback ??= signal(0),
);

void bumpJobsForYouEpoch() {
  jobsForYouEpoch.value = jobsForYouEpoch.value + 1;
}

import 'package:scoped_deps/scoped_deps.dart';
import 'package:signals/signals_flutter.dart';

/// Bumped after Job preferences save so Jobs For You reloads.
///
/// Jobs remounts when switching shell tabs (active-branch shell). Epoch still
/// matters when prefs save while Settings is pushed over an open Jobs tab.
final jobsForYouEpochRef = create(() => signal(0));

/// Last successful shortlist + notify chrome — survives Jobs screen dispose.
final jobsForYouCacheRef = create(() => signal<JobsForYouSnapshot?>(null));

Signal<int>? _jobsForYouEpochFallback;
Signal<JobsForYouSnapshot?>? _jobsForYouCacheFallback;

Signal<int> get jobsForYouEpoch => read(
  jobsForYouEpochRef,
  orElse: () => _jobsForYouEpochFallback ??= signal(0),
);

Signal<JobsForYouSnapshot?> get jobsForYouCache => read(
  jobsForYouCacheRef,
  orElse: () => _jobsForYouCacheFallback ??= signal(null),
);

/// Cached Jobs For You payload (shortlist + notification banner fields).
class JobsForYouSnapshot {
  const JobsForYouSnapshot({
    required this.items,
    required this.emptyReason,
    required this.cap,
    required this.capIsDefault,
    required this.unreadCount,
    required this.unreadIds,
    this.latestNotifySummary,
  });

  final List<Map<String, dynamic>> items;
  final String? emptyReason;
  final int cap;
  final bool capIsDefault;
  final int unreadCount;
  final Set<String> unreadIds;
  final String? latestNotifySummary;

  /// True when [currentUnreadIds] includes any notification not in this snapshot.
  bool hasNewUnread(Iterable<String> currentUnreadIds) {
    for (final id in currentUnreadIds) {
      if (!unreadIds.contains(id)) return true;
    }
    return false;
  }

  JobsForYouSnapshot copyWithNotifications({
    required int unreadCount,
    required Set<String> unreadIds,
    String? latestNotifySummary,
  }) {
    return JobsForYouSnapshot(
      items: items,
      emptyReason: emptyReason,
      cap: cap,
      capIsDefault: capIsDefault,
      unreadCount: unreadCount,
      unreadIds: unreadIds,
      latestNotifySummary: latestNotifySummary,
    );
  }
}

void bumpJobsForYouEpoch() {
  clearJobsForYouCache();
  jobsForYouEpoch.value = jobsForYouEpoch.value + 1;
}

void clearJobsForYouCache() {
  jobsForYouCache.value = null;
}

void storeJobsForYouCache(JobsForYouSnapshot snapshot) {
  jobsForYouCache.value = snapshot;
}

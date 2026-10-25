import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:signals/signals_flutter.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../../tailor/ui/tailor_screen.dart';
import '../services/job_discovery_service.dart';
import '../state/jobs_for_you_state.dart';

/// Personalized shortlist tab — mirrors `prototypes/job-discovery/`.
///
/// Phase 0: empty reasons from the API (`no_preferences` / `no_matches`).
/// Location + search filter client-side once items exist (Phase 2).
class JobsForYouScreen extends StatefulWidget {
  const JobsForYouScreen({super.key});

  @override
  State<JobsForYouScreen> createState() => _JobsForYouScreenState();
}

class _JobsForYouScreenState extends State<JobsForYouScreen> {
  final _service = JobDiscoveryService();
  final _searchController = TextEditingController();
  final _careersUrlController = TextEditingController();

  bool _loading = true;
  String? _error;
  String? _emptyReason;
  List<Map<String, dynamic>> _items = [];
  int _cap = 10;
  bool _capIsDefault = true;
  String _location = 'all';
  String _titleFilter = 'all';
  int _seenEpoch = -1;
  EffectCleanup? _epochCleanup;

  bool _submittingBoard = false;
  String? _boardMessage;
  String? _boardError;
  int _unreadNotifications = 0;
  String? _latestNotifySummary;

  @override
  void initState() {
    super.initState();
    _searchController.addListener(() => setState(() {}));
    _epochCleanup = effect(() {
      final epoch = jobsForYouEpoch.value;
      if (_seenEpoch == -1) {
        _seenEpoch = epoch;
        return;
      }
      if (epoch == _seenEpoch) return;
      _seenEpoch = epoch;
      // Epoch bump already clears [jobsForYouCache]; force network refresh.
      _load();
    });
    _mount();
  }

  @override
  void dispose() {
    _epochCleanup?.call();
    _searchController.dispose();
    _careersUrlController.dispose();
    super.dispose();
  }

  /// Hydrate from dispose-surviving cache when warm; otherwise full fetch.
  ///
  /// Active-branch shell disposes this screen on tab leave — cache must live
  /// in [jobsForYouCache], not only in State fields.
  Future<void> _mount() async {
    final cache = jobsForYouCache.value;
    if (cache != null) {
      _applySnapshot(cache);
      await _refreshIfNewRecommendations(cache);
      return;
    }
    await _load();
  }

  void _applySnapshot(JobsForYouSnapshot snapshot) {
    setState(() {
      _items = snapshot.items.map((e) => Map<String, dynamic>.from(e)).toList();
      _emptyReason = snapshot.emptyReason;
      _cap = snapshot.cap;
      _capIsDefault = snapshot.capIsDefault;
      _unreadNotifications = snapshot.unreadCount;
      _latestNotifySummary = snapshot.latestNotifySummary;
      _error = null;
      _loading = false;
    });
  }

  /// Light unread poll — refetch shortlist only when new strong-match IDs appear.
  Future<void> _refreshIfNewRecommendations(JobsForYouSnapshot cache) async {
    try {
      final notify = await _fetchNotifications();
      if (!mounted) return;
      if (cache.hasNewUnread(notify.ids)) {
        await _load();
        return;
      }
      setState(() {
        _unreadNotifications = notify.unreadCount;
        _latestNotifySummary = notify.summary;
      });
      storeJobsForYouCache(
        cache.copyWithNotifications(
          unreadCount: notify.unreadCount,
          unreadIds: notify.ids,
          latestNotifySummary: notify.summary,
        ),
      );
    } on Object {
      // Stay on cached shortlist if the light check fails.
    }
  }

  /// Always hits the shortlist API (pull-to-refresh, retry, epoch, cold mount).
  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await _service.jobsForYou();
      if (!mounted) return;
      final rawItems = data['items'];
      final items = rawItems is List
          ? rawItems
                .whereType<Map>()
                .map((e) => Map<String, dynamic>.from(e))
                .toList()
          : <Map<String, dynamic>>[];
      final emptyReason = data['empty_reason']?.toString();
      final cap = (data['cap'] as num?)?.toInt() ?? 10;
      final capIsDefault = data['cap_is_default'] != false;

      var unread = 0;
      var unreadIds = <String>{};
      String? summary;
      try {
        final notify = await _fetchNotifications();
        unread = notify.unreadCount;
        unreadIds = notify.ids;
        summary = notify.summary;
      } on Object {
        // Notifications are optional chrome; shortlist still works.
      }
      if (!mounted) return;

      final snapshot = JobsForYouSnapshot(
        items: items,
        emptyReason: emptyReason,
        cap: cap,
        capIsDefault: capIsDefault,
        unreadCount: unread,
        unreadIds: unreadIds,
        latestNotifySummary: summary,
      );
      storeJobsForYouCache(snapshot);
      setState(() {
        _items = items;
        _emptyReason = emptyReason;
        _cap = cap;
        _capIsDefault = capIsDefault;
        _unreadNotifications = unread;
        _latestNotifySummary = summary;
        _loading = false;
      });
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = _dioMessage(e);
        _loading = false;
      });
    } on Object catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
        _loading = false;
      });
    }
  }

  Future<({int unreadCount, Set<String> ids, String? summary})>
  _fetchNotifications() async {
    final data = await _service.matchNotifications(unreadOnly: true);
    final unread = (data['unread_count'] as num?)?.toInt() ?? 0;
    final rawItems = data['items'];
    final ids = <String>{};
    String? summary;
    if (rawItems is List) {
      for (final entry in rawItems) {
        if (entry is! Map) continue;
        final id = entry['id']?.toString();
        if (id != null && id.isNotEmpty) ids.add(id);
      }
      if (rawItems.isNotEmpty) {
        final first = rawItems.first;
        if (first is Map) {
          final title = first['title']?.toString() ?? '';
          final company = first['company']?.toString() ?? '';
          if (title.isNotEmpty) {
            summary = company.isEmpty ? title : '$title · $company';
          }
        }
      }
    }
    return (unreadCount: unread, ids: ids, summary: summary);
  }

  Future<void> _submitCareersUrl() async {
    final url = _careersUrlController.text.trim();
    if (url.isEmpty) {
      setState(() {
        _boardError = 'Paste a Greenhouse, Lever, or Ashby careers URL.';
        _boardMessage = null;
      });
      return;
    }
    setState(() {
      _submittingBoard = true;
      _boardError = null;
      _boardMessage = null;
    });
    try {
      final data = await _service.addBoardFromUrl(url);
      if (!mounted) return;
      setState(() {
        _submittingBoard = false;
        _boardMessage =
            data['message']?.toString() ??
            'Board added for everyone. Jobs appear after the next ingest.';
        _careersUrlController.clear();
      });
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() {
        _submittingBoard = false;
        _boardError = _dioMessage(e);
      });
    } on Object catch (e) {
      if (!mounted) return;
      setState(() {
        _submittingBoard = false;
        _boardError = '$e';
      });
    }
  }

  String _dioMessage(DioException error) {
    final detail = error.response?.data;
    if (detail is Map) {
      final nested = detail['detail'];
      if (nested is Map && nested['message'] != null) {
        return nested['message'].toString();
      }
      if (nested != null) return nested.toString();
    }
    return error.message ?? 'Couldn’t load jobs';
  }

  List<String> get _preferredTitles {
    final titles = <String>{};
    for (final item in _items) {
      final t = item['matched_title']?.toString().trim();
      if (t != null && t.isNotEmpty) titles.add(t);
    }
    return titles.toList()..sort();
  }

  List<Map<String, dynamic>> get _filtered {
    final q = _searchController.text.trim().toLowerCase();
    return _items.where((item) {
      if (_titleFilter != 'all') {
        final matched = item['matched_title']?.toString() ?? '';
        if (matched != _titleFilter) return false;
      }
      if (_location != 'all') {
        final loc = (item['location_raw']?.toString() ?? '').toLowerCase();
        if (_location == 'remote' && !loc.contains('remote')) return false;
        if (_location != 'remote' && !loc.contains(_location.toLowerCase())) {
          return false;
        }
      }
      if (q.isEmpty) return true;
      final hay = '${item['title']} ${item['company']} ${item['matched_title']}'
          .toLowerCase();
      return hay.contains(q);
    }).toList();
  }

  void _openMatchPrefs() => context.push('/settings/match-preferences');

  Future<void> _openJob(Map<String, dynamic> item) async {
    final postingId = item['posting_id']?.toString();
    if (postingId != null && postingId.isNotEmpty) {
      try {
        await _service.markOpened(postingId);
      } on Object {
        // Prefill still works if the open mark fails.
      }
    }
    if (!mounted) return;
    await context.push(
      '/tailor',
      extra: TailorLaunchArgs(
        company: item['company']?.toString(),
        targetRole: item['title']?.toString(),
        jobDescription:
            item['description_text']?.toString() ??
            item['job_description']?.toString(),
        postingId: postingId,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final scheme = Theme.of(context).colorScheme;
    final filtered = _filtered;
    final showListChrome =
        !_loading &&
        _error == null &&
        _emptyReason == null &&
        _items.isNotEmpty;
    final showSearchEmpty =
        showListChrome && filtered.isEmpty && _items.isNotEmpty;
    final prefsConfigured =
        !_loading &&
        _error == null &&
        (_emptyReason == null || _emptyReason == 'no_matches');

    final pageWidth = MediaQuery.sizeOf(context).width;
    final contentWidth = pageWidth < 960 + AppSpacing.grid * 6
        ? pageWidth - AppSpacing.grid * 6
        : 960.0;

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(
          AppSpacing.grid * 3,
          AppSpacing.grid * 3,
          AppSpacing.grid * 3,
          AppSpacing.grid * 6,
        ),
        physics: const AlwaysScrollableScrollPhysics(),
        children: [
          // LayoutBuilder gets the ListView's finite cross-axis width; a bare
          // Align+SizedBox still allowed PasteCareersUrl's Row to see Infinity.
          LayoutBuilder(
            builder: (context, constraints) {
              final maxCross = constraints.maxWidth.isFinite
                  ? constraints.maxWidth
                  : contentWidth;
              final width = maxCross < 960 ? maxCross : 960.0;
              return SizedBox(
                width: width,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (prefsConfigured) ...[
                      Text(
                        'Personalized for your preferences',
                        style: type.bodySmall?.copyWith(
                          color: scheme.primary,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: AppSpacing.grid),
                      Text(
                        'Jobs For You',
                        style: type.headlineMedium?.copyWith(
                          fontSize: 32,
                          letterSpacing: -0.035 * 32,
                        ),
                      ),
                      const SizedBox(height: AppSpacing.grid * 1.5),
                      Text(
                        'Roles that passed your title, place, and seniority '
                        'filters — ranked by fit to your profile.',
                        style: type.bodyMedium?.copyWith(
                          color: colors.muted,
                          height: 1.45,
                          fontWeight: FontWeight.w400,
                        ),
                      ),
                      const SizedBox(height: AppSpacing.grid * 3),
                    ],
                    if (_unreadNotifications > 0) ...[
                      _NotifyBanner(
                        count: _unreadNotifications,
                        summary: _latestNotifySummary,
                      ),
                      const SizedBox(height: AppSpacing.grid * 2),
                    ],
                    if (_error != null) ...[
                      _ErrorBanner(message: _error!, onRetry: _load),
                      const SizedBox(height: AppSpacing.grid * 2),
                    ],
                    if (_loading) const _LoadingSkeleton(),
                    if (!_loading &&
                        _error == null &&
                        _emptyReason == 'no_preferences')
                      _EmptyNoPreferences(onOpenPrefs: _openMatchPrefs),
                    if (!_loading &&
                        _error == null &&
                        _emptyReason == 'no_matches')
                      _EmptyNoMatches(onEditPrefs: _openMatchPrefs),
                    if (showListChrome || showSearchEmpty) ...[
                      _Toolbar(
                        location: _location,
                        searchController: _searchController,
                        onLocation: (v) => setState(() => _location = v),
                        contentWidth: contentWidth.clamp(0.0, 960.0),
                      ),
                      const SizedBox(height: AppSpacing.grid * 3),
                      Builder(
                        builder: (context) {
                          final wide = contentWidth >= 720;
                          final sidebar = _TitleSidebar(
                            titles: _preferredTitles,
                            selected: _titleFilter,
                            totalCount: _items.length,
                            onSelect: (v) => setState(() => _titleFilter = v),
                            onEditPrefs: _openMatchPrefs,
                          );
                          final results = Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              Wrap(
                                crossAxisAlignment: WrapCrossAlignment.center,
                                spacing: AppSpacing.grid,
                                runSpacing: AppSpacing.grid,
                                children: [
                                  Text(
                                    _titleFilter == 'all'
                                        ? 'Top matches'
                                        : _titleFilter,
                                    style: type.titleMedium?.copyWith(
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                  Text(
                                    _capIsDefault
                                        ? '${filtered.length} showing · default cap ($_cap)'
                                        : '${filtered.length} showing',
                                    style: type.bodySmall?.copyWith(
                                      color: colors.muted,
                                      fontWeight: FontWeight.w500,
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: AppSpacing.grid * 2),
                              if (showSearchEmpty)
                                _EmptySearch(
                                  onClear: () {
                                    _searchController.clear();
                                    setState(() {
                                      _location = 'all';
                                      _titleFilter = 'all';
                                    });
                                  },
                                )
                              else
                                ...filtered.map(
                                  (item) => Padding(
                                    padding: const EdgeInsets.only(
                                      bottom: AppSpacing.grid * 2,
                                    ),
                                    child: _JobCard(
                                      item: item,
                                      onTap: () => _openJob(item),
                                    ),
                                  ),
                                ),
                            ],
                          );
                          if (!wide) {
                            return Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                sidebar,
                                const SizedBox(height: AppSpacing.grid * 3),
                                results,
                              ],
                            );
                          }
                          const sideW = 200.0;
                          const gap = AppSpacing.grid * 4;
                          final resultsW = (contentWidth - sideW - gap).clamp(
                            240.0,
                            760.0,
                          );
                          return Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              SizedBox(width: sideW, child: sidebar),
                              const SizedBox(width: gap),
                              SizedBox(width: resultsW, child: results),
                            ],
                          );
                        },
                      ),
                    ],
                    // Below shortlist / empty states so helper copy never
                    // competes with the page title.
                    if (!_loading && _error == null) ...[
                      const SizedBox(height: AppSpacing.grid * 4),
                      _PasteCareersUrl(
                        controller: _careersUrlController,
                        submitting: _submittingBoard,
                        message: _boardMessage,
                        error: _boardError,
                        onSubmit: _submitCareersUrl,
                      ),
                    ],
                  ],
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}

class _NotifyBanner extends StatelessWidget {
  const _NotifyBanner({required this.count, this.summary});

  final int count;
  final String? summary;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;
    final colors = context.appColors;
    final lead = count == 1
        ? '1 new strong match'
        : '$count new strong matches';
    return Container(
      padding: const EdgeInsets.all(AppSpacing.grid * 2),
      decoration: BoxDecoration(
        color: scheme.primary.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(AppSpacing.markRadius + 2),
        border: Border.all(color: scheme.primary.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            lead,
            style: type.titleSmall?.copyWith(
              color: scheme.primary,
              fontWeight: FontWeight.w700,
            ),
          ),
          if (summary != null && summary!.isNotEmpty) ...[
            const SizedBox(height: AppSpacing.grid * 0.5),
            Text(
              summary!,
              style: type.bodySmall?.copyWith(
                color: colors.muted,
                fontWeight: FontWeight.w400,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _PasteCareersUrl extends StatelessWidget {
  const _PasteCareersUrl({
    required this.controller,
    required this.submitting,
    required this.onSubmit,
    this.message,
    this.error,
  });

  final TextEditingController controller;
  final bool submitting;
  final VoidCallback onSubmit;
  final String? message;
  final String? error;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final scheme = Theme.of(context).colorScheme;

    return DecoratedBox(
      decoration: BoxDecoration(
        border: Border(
          top: BorderSide(color: scheme.onSurface.withValues(alpha: 0.08)),
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.only(top: AppSpacing.grid * 3),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Add a company board',
              style: type.titleSmall?.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: AppSpacing.grid),
            Text(
              'Paste a Greenhouse, Lever, or Ashby careers URL — jobs appear '
              'after the next ingest.',
              style: type.bodySmall?.copyWith(
                color: colors.muted,
                height: 1.4,
                fontWeight: FontWeight.w400,
              ),
            ),
            const SizedBox(height: AppSpacing.grid * 1.5),
            // Explicit widths from MediaQuery — never Expanded/Row under a
            // Column that may pass tight infinite width on Flutter web.
            Builder(
              builder: (context) {
                const gap = AppSpacing.grid * 1.5;
                const buttonW = 96.0;
                final mq = MediaQuery.sizeOf(context).width;
                final fieldW = (mq - AppSpacing.grid * 6 - gap - buttonW).clamp(
                  160.0,
                  720.0,
                );
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SizedBox(
                      width: fieldW,
                      child: TextField(
                        controller: controller,
                        enabled: !submitting,
                        textInputAction: TextInputAction.done,
                        onSubmitted: (_) => onSubmit(),
                        decoration: const InputDecoration(
                          hintText: 'https://boards.greenhouse.io/…',
                        ),
                      ),
                    ),
                    const SizedBox(width: gap),
                    SizedBox(
                      width: buttonW,
                      child: FilledButton(
                        onPressed: submitting ? null : onSubmit,
                        child: Text(submitting ? 'Adding…' : 'Add'),
                      ),
                    ),
                  ],
                );
              },
            ),
            if (message != null) ...[
              const SizedBox(height: AppSpacing.grid),
              Text(
                message!,
                style: type.bodySmall?.copyWith(
                  color: scheme.primary,
                  height: 1.4,
                ),
              ),
            ],
            if (error != null) ...[
              const SizedBox(height: AppSpacing.grid),
              Text(
                error!,
                style: type.bodySmall?.copyWith(
                  color: scheme.error,
                  height: 1.4,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _Toolbar extends StatelessWidget {
  const _Toolbar({
    required this.location,
    required this.searchController,
    required this.onLocation,
    required this.contentWidth,
  });

  final String location;
  final TextEditingController searchController;
  final ValueChanged<String> onLocation;
  final double contentWidth;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final colors = context.appColors;
    final wide = contentWidth >= 560;
    final locationField = DropdownButtonFormField<String>(
      // ignore: deprecated_member_use — value still valid on stable
      value: location,
      isExpanded: true,
      icon: Text(
        '▾',
        style: TextStyle(
          fontSize: 14,
          height: 1,
          color: colors.muted,
          fontWeight: FontWeight.w600,
        ),
      ),
      decoration: const InputDecoration(
        contentPadding: EdgeInsets.symmetric(horizontal: 20, vertical: 12),
      ),
      items: const [
        DropdownMenuItem(value: 'all', child: Text('All locations')),
        DropdownMenuItem(value: 'remote', child: Text('Remote')),
        DropdownMenuItem(
          value: 'united kingdom',
          child: Text('United Kingdom'),
        ),
        DropdownMenuItem(value: 'ireland', child: Text('Ireland')),
        DropdownMenuItem(value: 'united states', child: Text('United States')),
        DropdownMenuItem(value: 'nigeria', child: Text('Nigeria')),
      ],
      onChanged: (v) {
        if (v != null) onLocation(v);
      },
    );
    final searchField = TextField(
      controller: searchController,
      decoration: InputDecoration(
        hintText: 'Search by company or role',
        filled: true,
        fillColor: scheme.surfaceContainerHighest,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppSpacing.pillRadius),
          borderSide: BorderSide.none,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppSpacing.pillRadius),
          borderSide: BorderSide.none,
        ),
        prefixIcon: Padding(
          padding: const EdgeInsets.only(left: 16, right: 8),
          child: Align(
            widthFactor: 1,
            alignment: Alignment.center,
            child: Text(
              '⌕',
              style: TextStyle(
                fontSize: 18,
                height: 1,
                color: colors.muted,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
        ),
        prefixIconConstraints: const BoxConstraints(
          minWidth: 40,
          minHeight: 24,
        ),
      ),
    );
    if (wide) {
      const locW = 200.0;
      const gap = AppSpacing.grid * 1.5;
      final searchW = (contentWidth - locW - gap).clamp(160.0, 760.0);
      return Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(width: locW, child: locationField),
          const SizedBox(width: gap),
          SizedBox(width: searchW, child: searchField),
        ],
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        locationField,
        const SizedBox(height: AppSpacing.grid * 1.5),
        searchField,
      ],
    );
  }
}

class _TitleSidebar extends StatelessWidget {
  const _TitleSidebar({
    required this.titles,
    required this.selected,
    required this.totalCount,
    required this.onSelect,
    required this.onEditPrefs,
  });

  final List<String> titles;
  final String selected;
  final int totalCount;
  final ValueChanged<String> onSelect;
  final VoidCallback onEditPrefs;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final scheme = Theme.of(context).colorScheme;

    Widget chip(String label, String value, int count) {
      final on = selected == value;
      return Padding(
        padding: const EdgeInsets.only(bottom: 4),
        child: Material(
          color: on
              ? scheme.primary.withValues(alpha: 0.1)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(AppSpacing.markRadius),
          child: InkWell(
            borderRadius: BorderRadius.circular(AppSpacing.markRadius),
            onTap: () => onSelect(value),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      label,
                      style: type.bodyMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                        color: on ? scheme.primary : colors.muted,
                      ),
                    ),
                  ),
                  Text(
                    '$count',
                    style: type.bodySmall?.copyWith(
                      color: on ? scheme.primary : colors.muted,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'YOUR TITLES',
          style: type.bodySmall?.copyWith(
            color: colors.muted,
            letterSpacing: 0.04 * 12,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: AppSpacing.grid),
        chip('All matches', 'all', totalCount),
        ...titles.map((t) {
          final count = totalCount; // Phase 2: per-title counts from API
          return chip(t, t, count);
        }),
        const SizedBox(height: AppSpacing.grid * 2),
        TextButton(
          onPressed: onEditPrefs,
          style: TextButton.styleFrom(
            alignment: Alignment.centerLeft,
            padding: EdgeInsets.zero,
            foregroundColor: colors.muted,
          ),
          child: const Text('Job preferences'),
        ),
      ],
    );
  }
}

class _JobCard extends StatelessWidget {
  const _JobCard({required this.item, required this.onTap});

  final Map<String, dynamic> item;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final scheme = Theme.of(context).colorScheme;
    final title = item['title']?.toString() ?? 'Role';
    final company = item['company']?.toString() ?? '';
    final location = item['location_raw']?.toString() ?? '';
    final reason = item['reason']?.toString() ?? '';

    return Material(
      color: scheme.surfaceContainerHighest,
      borderRadius: BorderRadius.circular(AppSpacing.markRadius + 4),
      child: InkWell(
        borderRadius: BorderRadius.circular(AppSpacing.markRadius + 4),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.grid * 3),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: type.titleMedium?.copyWith(
                  fontSize: 20,
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.02 * 20,
                ),
              ),
              if (company.isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(
                  company,
                  style: type.bodyMedium?.copyWith(
                    color: colors.label,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
              if (location.isNotEmpty) ...[
                const SizedBox(height: 10),
                Row(
                  children: [
                    Text(
                      '◎',
                      style: TextStyle(
                        fontSize: 12,
                        height: 1,
                        color: colors.muted,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        location,
                        style: type.bodySmall?.copyWith(
                          color: colors.muted,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
              if (reason.isNotEmpty) ...[
                const SizedBox(height: AppSpacing.grid * 2),
                Divider(
                  height: 1,
                  color: scheme.onSurface.withValues(alpha: 0.08),
                ),
                const SizedBox(height: AppSpacing.grid * 1.5),
                Text(
                  reason,
                  style: type.bodySmall?.copyWith(
                    color: scheme.primary,
                    fontWeight: FontWeight.w500,
                    height: 1.4,
                  ),
                ),
              ],
              const SizedBox(height: AppSpacing.grid * 2),
              Text(
                'Open to tailor →',
                style: type.bodySmall?.copyWith(fontWeight: FontWeight.w700),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _EmptyNoPreferences extends StatelessWidget {
  const _EmptyNoPreferences({required this.onOpenPrefs});

  final VoidCallback onOpenPrefs;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final scheme = Theme.of(context).colorScheme;

    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.grid * 4),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 420),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                color: scheme.primary.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(AppSpacing.markRadius + 4),
              ),
              alignment: Alignment.center,
              child: Text(
                '⚙',
                style: TextStyle(fontSize: 28, color: scheme.primary),
              ),
            ),
            const SizedBox(height: AppSpacing.grid * 2.5),
            Text(
              'Set Job preferences first',
              style: type.headlineMedium?.copyWith(fontSize: 22),
            ),
            const SizedBox(height: AppSpacing.grid * 1.25),
            Text(
              'Jobs For You needs titles, place, and seniority from your master '
              'resume. Set those in Settings — then we’ll surface strong matches '
              'here.',
              style: type.bodyMedium?.copyWith(
                color: colors.muted,
                height: 1.45,
                fontWeight: FontWeight.w400,
              ),
            ),
            const SizedBox(height: AppSpacing.grid * 3),
            OutlinedButton(
              onPressed: onOpenPrefs,
              child: const Text('Open Job preferences'),
            ),
          ],
        ),
      ),
    );
  }
}

class _EmptyNoMatches extends StatelessWidget {
  const _EmptyNoMatches({required this.onEditPrefs});

  final VoidCallback onEditPrefs;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final scheme = Theme.of(context).colorScheme;

    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.grid * 2),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 420),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                color: scheme.primary.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(AppSpacing.markRadius + 4),
              ),
              alignment: Alignment.center,
              child: Text(
                '∅',
                style: TextStyle(
                  fontSize: 28,
                  color: scheme.primary,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            const SizedBox(height: AppSpacing.grid * 2.5),
            Text(
              'No strong matches yet',
              style: type.headlineMedium?.copyWith(fontSize: 22),
            ),
            const SizedBox(height: AppSpacing.grid * 1.25),
            Text(
              'Nothing new passed your filters with a strong enough profile fit. '
              'Check back after the next ingest, or loosen location / titles in '
              'Job preferences.',
              style: type.bodyMedium?.copyWith(
                color: colors.muted,
                height: 1.45,
                fontWeight: FontWeight.w400,
              ),
            ),
            const SizedBox(height: AppSpacing.grid * 3),
            OutlinedButton(
              onPressed: onEditPrefs,
              child: const Text('Edit Job preferences'),
            ),
          ],
        ),
      ),
    );
  }
}

class _EmptySearch extends StatelessWidget {
  const _EmptySearch({required this.onClear});

  final VoidCallback onClear;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final scheme = Theme.of(context).colorScheme;

    return Container(
      padding: const EdgeInsets.all(AppSpacing.grid * 5),
      decoration: BoxDecoration(
        color: scheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(AppSpacing.markRadius + 4),
      ),
      child: Column(
        children: [
          Text(
            'No results found',
            style: type.titleMedium?.copyWith(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: AppSpacing.grid),
          Text(
            'Nothing matches that company, role, or location.',
            textAlign: TextAlign.center,
            style: type.bodyMedium?.copyWith(
              color: colors.muted,
              fontWeight: FontWeight.w400,
            ),
          ),
          const SizedBox(height: AppSpacing.grid * 2),
          OutlinedButton(
            onPressed: onClear,
            child: const Text('Clear filters'),
          ),
        ],
      ),
    );
  }
}

class _ErrorBanner extends StatelessWidget {
  const _ErrorBanner({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.all(AppSpacing.grid * 2),
      decoration: BoxDecoration(
        color: scheme.errorContainer,
        borderRadius: BorderRadius.circular(AppSpacing.markRadius),
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(
              message,
              style: TextStyle(
                color: scheme.onErrorContainer,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          TextButton(
            onPressed: onRetry,
            style: TextButton.styleFrom(foregroundColor: scheme.error),
            child: const Text('Retry'),
          ),
        ],
      ),
    );
  }
}

class _LoadingSkeleton extends StatelessWidget {
  const _LoadingSkeleton();

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    Widget block({double h = 18, double w = double.infinity}) => Container(
      height: h,
      width: w,
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(
        color: scheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(6),
      ),
    );

    return Column(
      children: List.generate(
        2,
        (_) => Container(
          margin: const EdgeInsets.only(bottom: AppSpacing.grid * 2),
          padding: const EdgeInsets.all(AppSpacing.grid * 3),
          decoration: BoxDecoration(
            color: scheme.surfaceContainerHighest.withValues(alpha: 0.5),
            borderRadius: BorderRadius.circular(AppSpacing.markRadius + 4),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              block(h: 22, w: 220),
              block(h: 14, w: 140),
              block(h: 12, w: 280),
            ],
          ),
        ),
      ),
    );
  }
}

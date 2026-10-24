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

  @override
  void initState() {
    super.initState();
    _load();
    _searchController.addListener(() => setState(() {}));
    _epochCleanup = effect(() {
      final epoch = jobsForYouEpoch.value;
      if (_seenEpoch == -1) {
        _seenEpoch = epoch;
        return;
      }
      if (epoch == _seenEpoch) return;
      _seenEpoch = epoch;
      _load();
    });
  }

  @override
  void dispose() {
    _epochCleanup?.call();
    _searchController.dispose();
    super.dispose();
  }

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
      setState(() {
        _items = items;
        _emptyReason = data['empty_reason']?.toString();
        _cap = (data['cap'] as num?)?.toInt() ?? 10;
        _capIsDefault = data['cap_is_default'] != false;
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

  void _openJob(Map<String, dynamic> item) {
    context.push(
      '/tailor',
      extra: TailorLaunchArgs(
        company: item['company']?.toString(),
        targetRole: item['title']?.toString(),
        jobDescription:
            item['description_text']?.toString() ??
            item['job_description']?.toString(),
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
          Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 960),
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
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          child: Text(
                            'Jobs For You',
                            style: type.headlineMedium?.copyWith(
                              fontSize: 32,
                              letterSpacing: -0.035 * 32,
                            ),
                          ),
                        ),
                        TextButton(
                          onPressed: _openMatchPrefs,
                          style: TextButton.styleFrom(
                            foregroundColor: colors.link,
                            padding: EdgeInsets.zero,
                            minimumSize: Size.zero,
                            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                          ),
                          child: const Text('Job preferences'),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.grid * 1.5),
                    Text(
                      'Fresh roles that passed your title, place, and seniority '
                      'filters — ranked by fit to your profile.',
                      style: type.bodyMedium?.copyWith(
                        color: colors.muted,
                        height: 1.45,
                        fontWeight: FontWeight.w400,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.grid * 3),
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
                    ),
                    const SizedBox(height: AppSpacing.grid * 3),
                    LayoutBuilder(
                      builder: (context, constraints) {
                        final wide = constraints.maxWidth >= 720;
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
                            Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    _titleFilter == 'all'
                                        ? 'Top matches'
                                        : _titleFilter,
                                    style: type.titleMedium?.copyWith(
                                      fontWeight: FontWeight.w700,
                                    ),
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
                        return Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            SizedBox(width: 200, child: sidebar),
                            const SizedBox(width: AppSpacing.grid * 4),
                            Expanded(child: results),
                          ],
                        );
                      },
                    ),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Toolbar extends StatelessWidget {
  const _Toolbar({
    required this.location,
    required this.searchController,
    required this.onLocation,
  });

  final String location;
  final TextEditingController searchController;
  final ValueChanged<String> onLocation;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Wrap(
      spacing: AppSpacing.grid * 1.5,
      runSpacing: AppSpacing.grid * 1.5,
      children: [
        SizedBox(
          width: 200,
          child: DropdownButtonFormField<String>(
            // ignore: deprecated_member_use — value still valid on stable
            value: location,
            decoration: const InputDecoration(
              contentPadding: EdgeInsets.symmetric(
                horizontal: 20,
                vertical: 12,
              ),
            ),
            items: const [
              DropdownMenuItem(value: 'all', child: Text('All locations')),
              DropdownMenuItem(value: 'remote', child: Text('Remote')),
              DropdownMenuItem(
                value: 'united kingdom',
                child: Text('United Kingdom'),
              ),
              DropdownMenuItem(value: 'ireland', child: Text('Ireland')),
              DropdownMenuItem(
                value: 'united states',
                child: Text('United States'),
              ),
              DropdownMenuItem(value: 'nigeria', child: Text('Nigeria')),
            ],
            onChanged: (v) {
              if (v != null) onLocation(v);
            },
          ),
        ),
        SizedBox(
          width: 320,
          child: TextField(
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
              prefixIcon: const Icon(Icons.search, size: 20),
            ),
          ),
        ),
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
            foregroundColor: colors.link,
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
                    Icon(Icons.place_outlined, size: 16, color: colors.muted),
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
              child: Icon(Icons.tune, color: scheme.primary),
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
            FilledButton(
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
              child: Icon(Icons.search_off, color: scheme.primary),
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

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:signals/signals_flutter.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../services/applications_service.dart';
import '../state/applications_state.dart';

class ApplicationsListScreen extends StatefulWidget {
  const ApplicationsListScreen({super.key});

  @override
  State<ApplicationsListScreen> createState() => _ApplicationsListScreenState();
}

class _ApplicationsListScreenState extends State<ApplicationsListScreen> {
  final _service = ApplicationsService();

  bool _loading = true;
  String? _error;
  List<Map<String, dynamic>> _items = [];
  int _seenEpoch = -1;
  EffectCleanup? _epochCleanup;

  @override
  void initState() {
    super.initState();
    _load();
    _epochCleanup = effect(() {
      final epoch = applicationsEpoch.value;
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
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final items = await _service.list();
      if (!mounted) return;
      setState(() {
        _items = items;
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
    if (detail is Map && detail['detail'] != null) {
      return detail['detail'].toString();
    }
    return error.message ?? 'Couldn’t load applications';
  }

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;

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
              constraints: const BoxConstraints(maxWidth: 720),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (!_loading && _items.isNotEmpty) ...[
                    Text(
                      '${_items.length} saved',
                      style: type.bodySmall?.copyWith(
                        color: colors.muted,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.grid * 2),
                  ],
                  if (_error != null) ...[
                    _ErrorAlert(message: _error!, onRetry: _load),
                    const SizedBox(height: AppSpacing.grid * 2),
                  ],
                  if (_loading)
                    const _SkeletonList()
                  else if (_items.isEmpty && _error == null)
                    _EmptyState(onTailor: () => context.push('/tailor'))
                  else
                    ..._items.map(
                      (item) => _ApplicationRow(
                        item: item,
                        onTap: () {
                          final id = item['id']?.toString();
                          if (id == null || id.isEmpty) return;
                          context.go('/applications/$id');
                        },
                      ),
                    ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.onTailor});

  final VoidCallback onTailor;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final scheme = Theme.of(context).colorScheme;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.grid * 4),
      child: Column(
        children: [
          DecoratedBox(
            decoration: BoxDecoration(
              color: scheme.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(16),
            ),
            child: const SizedBox(
              width: 72,
              height: 72,
              child: Icon(Icons.description_outlined, size: 32),
            ),
          ),
          const SizedBox(height: AppSpacing.grid * 3),
          Text(
            'No applications yet',
            style: type.titleMedium?.copyWith(
              fontWeight: FontWeight.w700,
              fontSize: 18,
            ),
          ),
          const SizedBox(height: AppSpacing.grid * 1.5),
          Text(
            'Tailor your first job description. Drafts show up here with '
            'company, role, and a short snippet so you can tell versions apart.',
            textAlign: TextAlign.center,
            style: type.bodyMedium?.copyWith(
              color: colors.muted,
              height: 1.45,
              fontWeight: FontWeight.w400,
            ),
          ),
          const SizedBox(height: AppSpacing.grid * 3),
          FilledButton(
            onPressed: onTailor,
            child: const Text('Tailor a job description'),
          ),
        ],
      ),
    );
  }
}

class _ErrorAlert extends StatelessWidget {
  const _ErrorAlert({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;

    return DecoratedBox(
      decoration: BoxDecoration(
        color: scheme.errorContainer,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.grid * 2),
        child: Row(
          children: [
            Expanded(
              child: Text(
                message.isEmpty
                    ? 'Couldn’t load applications. Check your connection '
                          'and try again.'
                    : message,
                style: type.bodyMedium?.copyWith(
                  color: scheme.error,
                  height: 1.4,
                ),
              ),
            ),
            TextButton(onPressed: onRetry, child: const Text('Retry')),
          ],
        ),
      ),
    );
  }
}

class _SkeletonList extends StatelessWidget {
  const _SkeletonList();

  @override
  Widget build(BuildContext context) {
    final soft = Theme.of(context).colorScheme.surfaceContainerHighest;
    return Column(
      children: List.generate(3, (_) {
        return Padding(
          padding: const EdgeInsets.only(bottom: AppSpacing.grid * 2),
          child: DecoratedBox(
            decoration: BoxDecoration(
              border: Border(bottom: BorderSide(color: soft, width: 1.5)),
            ),
            child: Padding(
              padding: const EdgeInsets.symmetric(
                vertical: AppSpacing.grid * 2,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _Skel(width: 220, height: 16, color: soft),
                  const SizedBox(height: 10),
                  _Skel(width: 140, height: 12, color: soft),
                  const SizedBox(height: 10),
                  _Skel(width: double.infinity, height: 12, color: soft),
                ],
              ),
            ),
          ),
        );
      }),
    );
  }
}

class _Skel extends StatelessWidget {
  const _Skel({required this.width, required this.height, required this.color});

  final double width;
  final double height;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(6),
      ),
    );
  }
}

class _ApplicationRow extends StatelessWidget {
  const _ApplicationRow({required this.item, required this.onTap});

  final Map<String, dynamic> item;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final scheme = Theme.of(context).colorScheme;

    final company = (item['company'] as String?)?.trim() ?? '';
    final role = (item['target_role'] as String?)?.trim() ?? '';
    final status = (item['status'] as String?)?.trim() ?? 'draft';
    final version = item['version'] as int? ?? 1;
    final snippet = (item['job_snippet'] as String?)?.trim() ?? '';
    final appliedAt = _parseDate(item['applied_at']);
    final createdAt = _parseDate(item['created_at']);
    final isApplied = status == 'applied';

    final titleParts = <String>[
      if (company.isNotEmpty) company else 'Untitled company',
      if (role.isNotEmpty) role else 'Untitled role',
    ];

    final metaDate = isApplied && appliedAt != null
        ? 'Applied ${_formatLong(appliedAt)}'
        : createdAt != null
        ? 'Created ${_formatLong(createdAt)}'
        : '';

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: DecoratedBox(
          decoration: BoxDecoration(
            border: Border(bottom: BorderSide(color: scheme.outline, width: 1)),
          ),
          child: Padding(
            padding: const EdgeInsets.symmetric(
              vertical: AppSpacing.grid * 2.5,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Text.rich(
                        TextSpan(
                          style: type.titleMedium?.copyWith(
                            fontWeight: FontWeight.w700,
                            fontSize: 17,
                            height: 1.25,
                          ),
                          children: [
                            TextSpan(text: titleParts.first),
                            if (titleParts.length > 1) ...[
                              TextSpan(
                                text: ' · ',
                                style: TextStyle(color: colors.muted),
                              ),
                              TextSpan(
                                text: titleParts[1],
                                style: type.titleMedium?.copyWith(
                                  fontWeight: FontWeight.w600,
                                  fontSize: 17,
                                  color: colors.label,
                                ),
                              ),
                            ],
                          ],
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const SizedBox(width: AppSpacing.grid),
                    _StatusBadge(applied: isApplied, appliedAt: appliedAt),
                  ],
                ),
                const SizedBox(height: AppSpacing.grid),
                Text(
                  ['v$version', if (metaDate.isNotEmpty) metaDate].join(' · '),
                  style: type.bodySmall?.copyWith(
                    color: colors.muted,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                if (snippet.isNotEmpty) ...[
                  const SizedBox(height: AppSpacing.grid),
                  Text(
                    snippet,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: type.bodySmall?.copyWith(
                      color: colors.muted,
                      fontWeight: FontWeight.w400,
                      height: 1.4,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.applied, this.appliedAt});

  final bool applied;
  final DateTime? appliedAt;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;
    final label = applied
        ? (appliedAt != null
              ? 'Applied ${_formatShort(appliedAt!)}'
              : 'Applied')
        : 'Draft';
    final bg = applied
        ? const Color(0xFFE8F2EE)
        : scheme.surfaceContainerHighest;
    final fg = applied ? scheme.primary : scheme.onSurface;

    return DecoratedBox(
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(AppSpacing.pillRadius),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.grid * 1.5,
          vertical: AppSpacing.grid * 0.75,
        ),
        child: Text(
          label,
          style: type.labelSmall?.copyWith(
            color: fg,
            fontWeight: FontWeight.w600,
            fontSize: 12,
          ),
        ),
      ),
    );
  }
}

DateTime? _parseDate(Object? raw) {
  if (raw is! String || raw.isEmpty) return null;
  return DateTime.tryParse(raw)?.toLocal();
}

const _months = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
];

String _formatLong(DateTime d) => '${d.day} ${_months[d.month - 1]} ${d.year}';

String _formatShort(DateTime d) => '${d.day} ${_months[d.month - 1]}';

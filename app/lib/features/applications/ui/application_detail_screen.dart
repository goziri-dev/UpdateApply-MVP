import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../../resume/widgets/resume_preview.dart';
import '../../tailor/ui/tailor_screen.dart';
import '../services/applications_service.dart';

class ApplicationDetailScreen extends StatefulWidget {
  const ApplicationDetailScreen({super.key, required this.applicationId});

  final String applicationId;

  @override
  State<ApplicationDetailScreen> createState() =>
      _ApplicationDetailScreenState();
}

class _ApplicationDetailScreenState extends State<ApplicationDetailScreen> {
  final _service = ApplicationsService();

  bool _loading = true;
  bool _marking = false;
  String? _error;
  Map<String, dynamic>? _detail;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(covariant ApplicationDetailScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.applicationId != widget.applicationId) {
      _load();
    }
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final detail = await _service.get(widget.applicationId);
      if (!mounted) return;
      setState(() {
        _detail = detail;
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
    return error.message ?? 'Couldn’t load application';
  }

  Future<void> _markApplied() async {
    setState(() => _marking = true);
    try {
      final updated = await _service.markApplied(widget.applicationId);
      if (!mounted) return;
      setState(() {
        _detail = updated;
        _marking = false;
      });
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('Marked as applied')));
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() => _marking = false);
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(_dioMessage(e))));
    } on Object catch (e) {
      if (!mounted) return;
      setState(() => _marking = false);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  void _tailorAgain() {
    final d = _detail;
    if (d == null) {
      context.push('/tailor');
      return;
    }
    context.push(
      '/tailor',
      extra: TailorLaunchArgs(
        company: d['company'] as String?,
        targetRole: d['target_role'] as String?,
        jobDescription: d['job_description'] as String?,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final scheme = Theme.of(context).colorScheme;
    final d = _detail;
    final company = (d?['company'] as String?)?.trim() ?? '';
    final role = (d?['target_role'] as String?)?.trim() ?? '';
    final status = (d?['status'] as String?)?.trim() ?? 'draft';
    final version = d?['version'] as int? ?? 1;
    final jd = (d?['job_description'] as String?)?.trim() ?? '';
    final applied = status == 'applied';
    final appliedAt = _parseDate(d?['applied_at']);
    final createdAt = _parseDate(d?['created_at']);
    final resume = d?['resume'];
    final resumeMap = resume is Map ? Map<String, dynamic>.from(resume) : null;

    final title = [
      if (company.isNotEmpty) company else 'Untitled company',
      if (role.isNotEmpty) role else 'Untitled role',
    ].join(' · ');

    final eyebrow = applied
        ? 'Version $version · Applied'
        : 'Version $version · Draft';
    final meta = applied && appliedAt != null
        ? 'Applied ${_formatLong(appliedAt)}'
        : createdAt != null
        ? 'Created ${_formatLong(createdAt)}'
        : '';

    return ListView(
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.grid * 3,
        AppSpacing.grid * 2,
        AppSpacing.grid * 3,
        AppSpacing.grid * 6,
      ),
      children: [
        Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 960),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton(
                    onPressed: () => context.go('/applications'),
                    style: TextButton.styleFrom(
                      foregroundColor: scheme.onSurface,
                      padding: EdgeInsets.zero,
                      minimumSize: Size.zero,
                      tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    ),
                    child: const Text('← Applications'),
                  ),
                ),
                const SizedBox(height: AppSpacing.grid * 2),
                if (_loading)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 48),
                    child: Center(child: CircularProgressIndicator()),
                  )
                else if (_error != null)
                  DecoratedBox(
                    decoration: BoxDecoration(
                      color: scheme.errorContainer,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.all(AppSpacing.grid * 2),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            _error!,
                            style: type.bodyMedium?.copyWith(
                              color: scheme.error,
                            ),
                          ),
                          TextButton(
                            onPressed: _load,
                            child: const Text('Retry'),
                          ),
                        ],
                      ),
                    ),
                  )
                else ...[
                  Text(
                    eyebrow,
                    style: type.bodySmall?.copyWith(
                      color: colors.muted,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: AppSpacing.grid),
                  Text(title, style: type.headlineMedium),
                  if (meta.isNotEmpty) ...[
                    const SizedBox(height: AppSpacing.grid),
                    Text(
                      meta,
                      style: type.bodyMedium?.copyWith(
                        color: colors.muted,
                        fontWeight: FontWeight.w400,
                      ),
                    ),
                  ],
                  const SizedBox(height: AppSpacing.grid * 3),
                  Wrap(
                    spacing: AppSpacing.grid,
                    runSpacing: AppSpacing.grid,
                    children: [
                      OutlinedButton(
                        onPressed: resumeMap == null
                            ? null
                            : () async {
                                await context.push(
                                  '/applications/${widget.applicationId}/edit',
                                );
                                if (mounted) await _load();
                              },
                        child: const Text('Edit resume'),
                      ),
                      OutlinedButton(
                        onPressed: resumeMap == null
                            ? null
                            : () =>
                                  downloadResumePdf(context, resume: resumeMap),
                        child: const Text('Download'),
                      ),
                      OutlinedButton(
                        onPressed: applied || _marking ? null : _markApplied,
                        child: _marking
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : Text(applied ? 'Applied' : 'Mark as applied'),
                      ),
                      FilledButton(
                        onPressed: _tailorAgain,
                        child: const Text('Tailor again'),
                      ),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.grid * 4),
                  LayoutBuilder(
                    builder: (context, constraints) {
                      final wide = constraints.maxWidth >= 800;
                      final preview = resumeMap == null
                          ? const SizedBox.shrink()
                          : Center(
                              child: ResumePreview(
                                mode: ResumePreviewMode.full,
                                resume: resumeMap,
                                viewTypePrefix:
                                    'resume-app-${widget.applicationId}',
                                maxWidth: 480,
                              ),
                            );
                      final jdPanel = _JdPanel(jobDescription: jd);
                      if (!wide) {
                        return Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            preview,
                            const SizedBox(height: AppSpacing.grid * 3),
                            jdPanel,
                          ],
                        );
                      }
                      return Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(flex: 3, child: preview),
                          const SizedBox(width: AppSpacing.grid * 3),
                          Expanded(flex: 2, child: jdPanel),
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
    );
  }
}

class _JdPanel extends StatelessWidget {
  const _JdPanel({required this.jobDescription});

  final String jobDescription;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final scheme = Theme.of(context).colorScheme;
    final snip = jobDescription.trim();

    return DecoratedBox(
      decoration: BoxDecoration(
        color: scheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.grid * 2.5),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'From the job description',
              style: type.bodySmall?.copyWith(
                color: colors.label,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: AppSpacing.grid * 1.5),
            Text(
              snip.isEmpty ? 'No job description saved.' : snip,
              maxLines: 12,
              overflow: TextOverflow.ellipsis,
              style: type.bodyMedium?.copyWith(
                height: 1.45,
                fontWeight: FontWeight.w400,
              ),
            ),
            const SizedBox(height: AppSpacing.grid * 2),
            Text(
              'Applied date is optional. Mark applied when you send it — '
              'drafts stay here until then.',
              style: type.bodySmall?.copyWith(
                color: colors.muted,
                fontWeight: FontWeight.w400,
                height: 1.4,
              ),
            ),
          ],
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

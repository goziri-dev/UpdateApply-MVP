import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../services/job_discovery_service.dart';
import '../state/jobs_for_you_state.dart';

const _seniorityOptions = <(String, String)>[
  ('junior', 'Junior'),
  ('mid', 'Mid'),
  ('senior', 'Senior'),
  ('staff_principal', 'Staff / Principal'),
  ('lead_manager', 'Lead / Manager'),
];

const _remoteOptions = <(String, String)>[
  ('remote_only', 'Remote only'),
  ('remote_ok', 'Hybrid'),
  ('onsite_only', 'On-site only'),
];

/// Settings → Job preferences (Phase 0 confirm-targets; API path unchanged).
class MatchPreferencesScreen extends StatefulWidget {
  const MatchPreferencesScreen({super.key});

  @override
  State<MatchPreferencesScreen> createState() => _MatchPreferencesScreenState();
}

class _MatchPreferencesScreenState extends State<MatchPreferencesScreen> {
  final _service = JobDiscoveryService();
  final _countriesController = TextEditingController();
  final _cityController = TextEditingController();

  bool _loading = true;
  bool _saving = false;
  bool _clearing = false;
  bool _hasSavedPrefs = false;
  String? _error;
  String? _suggestError;
  final List<TextEditingController> _titleControllers = [];
  final Set<String> _seniority = {'mid', 'senior'};
  String _remote = 'remote_ok';

  @override
  void initState() {
    super.initState();
    _bootstrap();
  }

  @override
  void dispose() {
    _countriesController.dispose();
    _cityController.dispose();
    for (final c in _titleControllers) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _bootstrap() async {
    setState(() {
      _loading = true;
      _error = null;
      _suggestError = null;
    });
    try {
      final prefs = await _service.getPreferences();
      if (!mounted) return;

      if (prefs != null) {
        _applyPrefs(prefs);
        setState(() {
          _hasSavedPrefs = true;
          _loading = false;
        });
        return;
      }

      // No saved prefs — load suggestions (may fail without profile / OpenRouter).
      try {
        final suggestions = await _service.suggestTitles();
        if (!mounted) return;
        _setTitles(
          suggestions
              .map((s) => s['title']?.toString().trim() ?? '')
              .where((t) => t.isNotEmpty)
              .toList(),
        );
      } on DioException catch (e) {
        if (!mounted) return;
        _suggestError = _dioMessage(e);
        if (_titleControllers.isEmpty) _addTitleField('');
      }
      setState(() {
        _hasSavedPrefs = false;
        _loading = false;
      });
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = _dioMessage(e);
        _loading = false;
        if (_titleControllers.isEmpty) _addTitleField('');
      });
    } on Object catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
        _loading = false;
        if (_titleControllers.isEmpty) _addTitleField('');
      });
    }
  }

  void _applyPrefs(Map<String, dynamic> prefs) {
    final titles = (prefs['titles'] is List)
        ? (prefs['titles'] as List)
              .map((e) => e.toString())
              .where((t) => t.trim().isNotEmpty)
              .toList()
        : <String>[];
    _setTitles(titles.isEmpty ? [''] : titles);

    final bands = prefs['seniority_bands'];
    _seniority
      ..clear()
      ..addAll(
        bands is List
            ? bands.map((e) => e.toString()).where((b) => b.isNotEmpty)
            : const <String>['mid', 'senior'],
      );
    if (_seniority.isEmpty) {
      _seniority.addAll({'mid', 'senior'});
    }

    final remote = prefs['remote_preference']?.toString();
    if (remote == 'remote_only' ||
        remote == 'remote_ok' ||
        remote == 'onsite_only') {
      _remote = remote!;
    }

    final countries = prefs['countries'];
    if (countries is List) {
      _countriesController.text = countries
          .map((e) => e.toString())
          .where((c) => c.trim().isNotEmpty)
          .join(', ');
    }
    _cityController.text = prefs['city']?.toString() ?? '';
  }

  void _setTitles(List<String> titles) {
    for (final c in _titleControllers) {
      c.dispose();
    }
    _titleControllers
      ..clear()
      ..addAll(titles.map((t) => TextEditingController(text: t)));
  }

  void _addTitleField([String value = '']) {
    setState(() {
      _titleControllers.add(TextEditingController(text: value));
    });
  }

  void _removeTitleAt(int index) {
    if (_titleControllers.length <= 1) return;
    setState(() {
      _titleControllers.removeAt(index).dispose();
    });
  }

  List<String> _parsedCountries() {
    return _countriesController.text
        .split(RegExp(r'[,;\n]'))
        .map((e) => e.trim())
        .where((e) => e.isNotEmpty)
        .toList();
  }

  Future<void> _save() async {
    final titles = _titleControllers
        .map((c) => c.text.trim())
        .where((t) => t.isNotEmpty)
        .toList();
    if (titles.isEmpty) {
      setState(() => _error = 'Add at least one preferred title.');
      return;
    }
    if (_seniority.isEmpty) {
      setState(() => _error = 'Pick at least one seniority band.');
      return;
    }

    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await _service.savePreferences(
        titles: titles,
        seniorityBands: _seniority.toList(),
        remotePreference: _remote,
        countries: _parsedCountries(),
        city: _cityController.text.trim().isEmpty
            ? null
            : _cityController.text.trim(),
      );
      if (!mounted) return;
      bumpJobsForYouEpoch();
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Job preferences saved — Jobs For You will use this set.',
          ),
        ),
      );
      context.go('/jobs');
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = _dioMessage(e);
        _saving = false;
      });
    } on Object catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
        _saving = false;
      });
    }
  }

  Future<void> _confirmClear() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) {
        final scheme = Theme.of(ctx).colorScheme;
        return AlertDialog(
          title: const Text('Clear job preferences?'),
          content: const Text(
            'Jobs For You will ask you to set preferences again. You can save '
            'a new set anytime.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(false),
              child: const Text('Cancel'),
            ),
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(true),
              style: TextButton.styleFrom(foregroundColor: scheme.error),
              child: const Text('Clear job preferences'),
            ),
          ],
        );
      },
    );
    if (confirmed != true || !mounted) return;
    await _clear();
  }

  Future<void> _clear() async {
    setState(() {
      _clearing = true;
      _error = null;
    });
    try {
      await _service.clearPreferences();
      if (!mounted) return;
      bumpJobsForYouEpoch();
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Job preferences cleared')));
      context.go('/jobs');
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = _dioMessage(e);
        _clearing = false;
      });
    } on Object catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
        _clearing = false;
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
    return error.message ?? 'Something went wrong';
  }

  void _goBack() {
    if (context.canPop()) {
      context.pop();
      return;
    }
    context.go('/settings');
  }

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final scheme = Theme.of(context).colorScheme;

    return Scaffold(
      backgroundColor: scheme.surface,
      body: SafeArea(
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : ListView(
                padding: const EdgeInsets.fromLTRB(
                  AppSpacing.grid * 3,
                  AppSpacing.grid * 2,
                  AppSpacing.grid * 3,
                  AppSpacing.grid * 8,
                ),
                children: [
                  Center(
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 520),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Align(
                            alignment: Alignment.centerLeft,
                            child: TextButton(
                              onPressed: _goBack,
                              style: TextButton.styleFrom(
                                foregroundColor: colors.muted,
                                padding: EdgeInsets.zero,
                                minimumSize: Size.zero,
                                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                              ),
                              child: const Text('← Settings'),
                            ),
                          ),
                          const SizedBox(height: AppSpacing.grid * 2),
                          Text(
                            'Jobs For You',
                            style: type.bodySmall?.copyWith(
                              color: scheme.primary,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(height: AppSpacing.grid),
                          Text('Job preferences', style: type.headlineMedium),
                          const SizedBox(height: AppSpacing.grid),
                          Text(
                            'We propose hiring titles from your master profile. '
                            'Edit the list, set place and seniority, then save. '
                            'These strings become the hard filter for Jobs For You.',
                            style: type.bodyMedium?.copyWith(
                              color: colors.muted,
                              height: 1.45,
                              fontWeight: FontWeight.w400,
                            ),
                          ),
                          if (_error != null) ...[
                            const SizedBox(height: AppSpacing.grid * 2),
                            _InlineAlert(message: _error!),
                          ],
                          if (_suggestError != null) ...[
                            const SizedBox(height: AppSpacing.grid * 2),
                            _InlineAlert(
                              message:
                                  'Couldn’t load suggestions: $_suggestError. '
                                  'You can still type titles manually.',
                              soft: true,
                            ),
                          ],
                          const SizedBox(height: AppSpacing.grid * 4),
                          _SectionHead(
                            title: 'Preferred titles',
                            actionLabel: 'Add title',
                            onAction: () => _addTitleField(),
                          ),
                          const SizedBox(height: AppSpacing.grid * 1.5),
                          ...List.generate(_titleControllers.length, (i) {
                            return Padding(
                              padding: const EdgeInsets.only(
                                bottom: AppSpacing.grid * 1.25,
                              ),
                              child: _TitleRow(
                                controller: _titleControllers[i],
                                onRemove: _titleControllers.length > 1
                                    ? () => _removeTitleAt(i)
                                    : null,
                              ),
                            );
                          }),
                          Text(
                            'Skill-shaped titles are not suggested. If you type '
                            'one and keep it, that exact string is what we filter on.',
                            style: type.labelSmall?.copyWith(
                              color: colors.muted,
                              height: 1.4,
                            ),
                          ),
                          const SizedBox(height: AppSpacing.grid * 4),
                          Text(
                            'Location or remote',
                            style: type.titleMedium?.copyWith(
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: AppSpacing.grid * 1.5),
                          Wrap(
                            spacing: AppSpacing.grid,
                            runSpacing: AppSpacing.grid,
                            children: _remoteOptions.map((opt) {
                              final on = _remote == opt.$1;
                              return ChoiceChip(
                                label: Text(opt.$2),
                                selected: on,
                                onSelected: (_) =>
                                    setState(() => _remote = opt.$1),
                              );
                            }).toList(),
                          ),
                          const SizedBox(height: AppSpacing.grid * 2),
                          Text(
                            'Countries',
                            style: type.bodySmall?.copyWith(
                              color: colors.label,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(height: AppSpacing.grid),
                          TextField(
                            controller: _countriesController,
                            decoration: const InputDecoration(
                              hintText: 'e.g. United Kingdom, Nigeria',
                            ),
                          ),
                          const SizedBox(height: AppSpacing.grid * 2),
                          Text(
                            'City (optional)',
                            style: type.bodySmall?.copyWith(
                              color: colors.label,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(height: AppSpacing.grid),
                          TextField(
                            controller: _cityController,
                            decoration: const InputDecoration(
                              hintText: 'e.g. London',
                            ),
                          ),
                          const SizedBox(height: AppSpacing.grid * 4),
                          Text(
                            'Seniority',
                            style: type.titleMedium?.copyWith(
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          const SizedBox(height: AppSpacing.grid * 1.5),
                          Wrap(
                            spacing: AppSpacing.grid,
                            runSpacing: AppSpacing.grid,
                            children: _seniorityOptions.map((opt) {
                              final on = _seniority.contains(opt.$1);
                              return FilterChip(
                                label: Text(opt.$2),
                                selected: on,
                                onSelected: (selected) {
                                  setState(() {
                                    if (selected) {
                                      _seniority.add(opt.$1);
                                    } else {
                                      _seniority.remove(opt.$1);
                                    }
                                  });
                                },
                              );
                            }).toList(),
                          ),
                          const SizedBox(height: AppSpacing.grid * 4),
                          Row(
                            children: [
                              Expanded(
                                child: OutlinedButton(
                                  onPressed: _saving || _clearing
                                      ? null
                                      : _goBack,
                                  child: const Text('Cancel'),
                                ),
                              ),
                              const SizedBox(width: AppSpacing.grid * 1.5),
                              Expanded(
                                child: FilledButton(
                                  onPressed: _saving || _clearing
                                      ? null
                                      : _save,
                                  child: Text(
                                    _saving ? 'Saving…' : 'Save preferences',
                                  ),
                                ),
                              ),
                            ],
                          ),
                          if (_hasSavedPrefs) ...[
                            const SizedBox(height: AppSpacing.grid * 3),
                            Text(
                              'Testing or starting over?',
                              style: type.titleSmall?.copyWith(
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const SizedBox(height: AppSpacing.grid),
                            Text(
                              'Clear saved preferences to return Jobs For You '
                              'to the set-up empty state.',
                              style: type.bodySmall?.copyWith(
                                color: colors.muted,
                                height: 1.4,
                                fontWeight: FontWeight.w400,
                              ),
                            ),
                            const SizedBox(height: AppSpacing.grid * 1.5),
                            OutlinedButton(
                              onPressed: _saving || _clearing
                                  ? null
                                  : _confirmClear,
                              style: OutlinedButton.styleFrom(
                                foregroundColor: scheme.error,
                                side: BorderSide(
                                  color: scheme.error.withValues(alpha: 0.45),
                                ),
                              ),
                              child: Text(
                                _clearing
                                    ? 'Clearing…'
                                    : 'Clear job preferences',
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}

class _SectionHead extends StatelessWidget {
  const _SectionHead({
    required this.title,
    required this.actionLabel,
    required this.onAction,
  });

  final String title;
  final String actionLabel;
  final VoidCallback onAction;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    return Row(
      children: [
        Expanded(
          child: Text(
            title,
            style: type.titleMedium?.copyWith(fontWeight: FontWeight.w700),
          ),
        ),
        TextButton(onPressed: onAction, child: Text(actionLabel)),
      ],
    );
  }
}

class _TitleRow extends StatelessWidget {
  const _TitleRow({required this.controller, this.onRemove});

  final TextEditingController controller;
  final VoidCallback? onRemove;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.only(left: 16, right: 4),
      decoration: BoxDecoration(
        color: scheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(AppSpacing.markRadius),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: controller,
              decoration: const InputDecoration(
                border: InputBorder.none,
                enabledBorder: InputBorder.none,
                focusedBorder: InputBorder.none,
                filled: false,
                hintText: 'e.g. Staff Product Designer',
              ),
            ),
          ),
          if (onRemove != null)
            IconButton(
              onPressed: onRemove,
              icon: const Icon(Icons.close),
              tooltip: 'Remove title',
            ),
        ],
      ),
    );
  }
}

class _InlineAlert extends StatelessWidget {
  const _InlineAlert({required this.message, this.soft = false});

  final String message;
  final bool soft;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final colors = context.appColors;
    return Container(
      padding: const EdgeInsets.all(AppSpacing.grid * 2),
      decoration: BoxDecoration(
        color: soft ? scheme.surfaceContainerHighest : scheme.errorContainer,
        borderRadius: BorderRadius.circular(AppSpacing.markRadius),
      ),
      child: Text(
        message,
        style: TextStyle(
          color: soft ? colors.muted : scheme.onErrorContainer,
          fontWeight: FontWeight.w500,
          height: 1.4,
        ),
      ),
    );
  }
}

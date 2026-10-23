import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../state/onboarding_state.dart';
import '../widgets/onboarding_feedback.dart';
import '../widgets/onboarding_shell.dart';

class OnboardingReviewScreen extends StatefulWidget {
  const OnboardingReviewScreen({super.key});

  @override
  State<OnboardingReviewScreen> createState() => _OnboardingReviewScreenState();
}

class _OnboardingReviewScreenState extends State<OnboardingReviewScreen> {
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _location = TextEditingController();
  final _links = TextEditingController();
  final _summary = TextEditingController();
  final _expSummaries = <TextEditingController>[];
  final _expBullets = <TextEditingController>[];
  final _projSummaries = <TextEditingController>[];
  final _projBullets = <TextEditingController>[];

  Map<String, dynamic> _data = {};
  List<Map<String, dynamic>> _experience = [];
  List<Map<String, dynamic>> _projects = [];
  List<String> _skills = [];
  bool _loading = true;
  bool _saving = false;
  String? _loadError;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    _location.dispose();
    _links.dispose();
    _summary.dispose();
    for (final c in _expSummaries) {
      c.dispose();
    }
    for (final c in _expBullets) {
      c.dispose();
    }
    for (final c in _projSummaries) {
      c.dispose();
    }
    for (final c in _projBullets) {
      c.dispose();
    }
    super.dispose();
  }

  void _disposeItemControllers() {
    for (final c in _expSummaries) {
      c.dispose();
    }
    for (final c in _expBullets) {
      c.dispose();
    }
    for (final c in _projSummaries) {
      c.dispose();
    }
    for (final c in _projBullets) {
      c.dispose();
    }
    _expSummaries.clear();
    _expBullets.clear();
    _projSummaries.clear();
    _projBullets.clear();
  }

  String _bulletsText(dynamic raw) {
    if (raw is! List) return '';
    return raw.map((e) => '$e'.trim()).where((e) => e.isNotEmpty).join('\n');
  }

  List<String> _bulletsFromText(String text) {
    return text
        .split('\n')
        .map((e) => e.trim())
        .where((e) => e.isNotEmpty)
        .toList();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _loadError = null;
    });
    clearOnboardingFeedback();
    try {
      // Remade master (idempotent). Do not load raw interview Q&A as Review.
      final generated = await onboardingService.generateReview();
      final data = Map<String, dynamic>.from(
        (generated['profile'] as Map?) ?? const {},
      );
      _applyProfile(data);
      if (!mounted) return;
      setState(() => _loading = false);
    } on DioException catch (e) {
      final message = _dioMessage(e);
      setOnboardingError(message);
      if (!mounted) return;
      setState(() {
        _loading = false;
        _loadError = message;
      });
    } on Object catch (e) {
      final message = e.toString();
      setOnboardingError(message);
      if (!mounted) return;
      setState(() {
        _loading = false;
        _loadError = message;
      });
    }
  }

  void _applyProfile(Map<String, dynamic> data) {
    final basics = Map<String, dynamic>.from(
      (data['basics'] as Map?) ?? const {},
    );
    final experience = (data['experience'] as List? ?? [])
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
    final projects = (data['projects'] as List? ?? [])
        .whereType<Map>()
        .map((e) => Map<String, dynamic>.from(e))
        .toList();
    final skills = <String>[];
    for (final group in data['skills'] as List? ?? []) {
      if (group is String) {
        skills.add(group);
      } else if (group is Map) {
        final keywords = group['keywords'] as List? ?? [];
        if (keywords.isNotEmpty) {
          skills.addAll(keywords.map((e) => '$e'));
        } else if (group['name'] != null) {
          skills.add('${group['name']}');
        }
      }
    }

    _disposeItemControllers();
    _expSummaries.addAll(
      experience.map(
        (e) => TextEditingController(text: '${e['summary'] ?? ''}'),
      ),
    );
    _expBullets.addAll(
      experience.map(
        (e) => TextEditingController(text: _bulletsText(e['bullets'])),
      ),
    );
    _projSummaries.addAll(
      projects.map((e) => TextEditingController(text: '${e['summary'] ?? ''}')),
    );
    _projBullets.addAll(
      projects.map(
        (e) => TextEditingController(text: _bulletsText(e['bullets'])),
      ),
    );

    _name.text = '${basics['name'] ?? ''}';
    _email.text = '${basics['email'] ?? ''}';
    _location.text = '${basics['location'] ?? ''}';
    final links = basics['links'];
    _links.text = links is List ? links.join(' · ') : '${links ?? ''}';
    _summary.text = '${data['summary'] ?? ''}';

    _data = data;
    _experience = experience;
    _projects = projects;
    _skills = skills;
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    clearOnboardingFeedback();
    try {
      final links = _links.text
          .split('·')
          .map((e) => e.trim())
          .where((e) => e.isNotEmpty)
          .toList();
      final experience = <Map<String, dynamic>>[];
      for (var i = 0; i < _experience.length; i++) {
        experience.add({
          ..._experience[i],
          'summary': _expSummaries[i].text.trim(),
          'bullets': _bulletsFromText(_expBullets[i].text),
        });
      }
      final projects = <Map<String, dynamic>>[];
      for (var i = 0; i < _projects.length; i++) {
        projects.add({
          ..._projects[i],
          'summary': _projSummaries[i].text.trim(),
          'bullets': _bulletsFromText(_projBullets[i].text),
        });
      }
      final payload = {
        ..._data,
        'basics': {
          ...Map<String, dynamic>.from((_data['basics'] as Map?) ?? {}),
          'name': _name.text.trim(),
          'email': _email.text.trim(),
          'location': _location.text.trim(),
          'links': links,
        },
        'summary': _summary.text.trim(),
        'experience': experience,
        'projects': projects,
      };
      await onboardingService.updateProfile(payload);
      if (!mounted) return;
      context.go('/onboarding/reveal');
    } on DioException catch (e) {
      setOnboardingError(_dioMessage(e));
    } on Object catch (e) {
      setOnboardingError(e.toString());
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  String _dioMessage(DioException e) {
    final detail = e.response?.data;
    if (detail is Map && detail['detail'] != null) {
      return detail['detail'].toString();
    }
    return e.message ?? 'Request failed';
  }

  InputDecoration _fieldDecoration(String label) {
    return InputDecoration(
      labelText: label,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
    );
  }

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final scheme = Theme.of(context).colorScheme;

    return OnboardingShell(
      stepLabel: '4 / 5',
      caption: 'Check the remade resume',
      onBack: () => context.go('/onboarding/interview'),
      child: _loading
          ? Padding(
              padding: const EdgeInsets.only(top: 48),
              child: Column(
                children: [
                  const CircularProgressIndicator(),
                  const SizedBox(height: AppSpacing.grid * 2),
                  Text(
                    'Rewriting your master resume…',
                    textAlign: TextAlign.center,
                    style: type.bodyMedium?.copyWith(
                      color: colors.muted,
                      height: 1.45,
                    ),
                  ),
                ],
              ),
            )
          : _loadError != null
          ? Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  'Couldn’t rewrite your resume',
                  style: type.headlineMedium,
                ),
                const SizedBox(height: AppSpacing.grid * 1.5),
                const OnboardingFeedbackBanner(),
                const SizedBox(height: AppSpacing.grid * 2),
                FilledButton(onPressed: _load, child: const Text('Try again')),
              ],
            )
          : Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text('Review your remade resume', style: type.headlineMedium),
                const SizedBox(height: AppSpacing.grid * 1.5),
                Text(
                  'We rewrote your master profile from your resume and '
                  'conversation. Correct anything we got wrong — this is what '
                  "you'll tailor later, not a replay of your answers.",
                  style: type.bodyMedium?.copyWith(
                    color: colors.muted,
                    height: 1.45,
                    fontWeight: FontWeight.w400,
                  ),
                ),
                const SizedBox(height: AppSpacing.grid * 2),
                const OnboardingFeedbackBanner(),
                Text('Basics', style: type.titleMedium),
                const SizedBox(height: AppSpacing.grid),
                TextField(
                  controller: _name,
                  decoration: _fieldDecoration('Full name'),
                ),
                const SizedBox(height: AppSpacing.grid),
                TextField(
                  controller: _email,
                  decoration: _fieldDecoration('Email'),
                ),
                const SizedBox(height: AppSpacing.grid),
                TextField(
                  controller: _location,
                  decoration: _fieldDecoration('Location'),
                ),
                const SizedBox(height: AppSpacing.grid),
                TextField(
                  controller: _links,
                  decoration: _fieldDecoration('Links'),
                ),
                const SizedBox(height: AppSpacing.grid),
                TextField(
                  controller: _summary,
                  maxLines: 4,
                  decoration: _fieldDecoration('Profile summary'),
                ),
                const SizedBox(height: AppSpacing.grid * 3),
                Text('Experience', style: type.titleMedium),
                const SizedBox(height: AppSpacing.grid),
                ...List.generate(_experience.length, (i) {
                  final e = _experience[i];
                  return Padding(
                    padding: const EdgeInsets.only(bottom: AppSpacing.grid * 3),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Text(
                          '${e['title'] ?? ''} · ${e['company'] ?? ''}',
                          style: type.bodyLarge,
                        ),
                        Text(
                          '${e['start'] ?? ''} — ${e['end'] ?? ''}',
                          style: type.bodySmall?.copyWith(color: colors.muted),
                        ),
                        const SizedBox(height: AppSpacing.grid),
                        TextField(
                          controller: _expSummaries[i],
                          maxLines: 3,
                          decoration: _fieldDecoration('Summary'),
                        ),
                        const SizedBox(height: AppSpacing.grid),
                        TextField(
                          controller: _expBullets[i],
                          maxLines: 5,
                          decoration: _fieldDecoration(
                            'Bullets (one per line)',
                          ),
                        ),
                      ],
                    ),
                  );
                }),
                Text('Projects', style: type.titleMedium),
                const SizedBox(height: AppSpacing.grid),
                ...List.generate(_projects.length, (i) {
                  final e = _projects[i];
                  return Padding(
                    padding: const EdgeInsets.only(bottom: AppSpacing.grid * 3),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Text('${e['title'] ?? ''}', style: type.bodyLarge),
                        Text(
                          '${e['start'] ?? ''} — ${e['end'] ?? ''}',
                          style: type.bodySmall?.copyWith(color: colors.muted),
                        ),
                        const SizedBox(height: AppSpacing.grid),
                        TextField(
                          controller: _projSummaries[i],
                          maxLines: 3,
                          decoration: _fieldDecoration('Summary'),
                        ),
                        const SizedBox(height: AppSpacing.grid),
                        TextField(
                          controller: _projBullets[i],
                          maxLines: 5,
                          decoration: _fieldDecoration(
                            'Bullets (one per line)',
                          ),
                        ),
                      ],
                    ),
                  );
                }),
                Text('Skills', style: type.titleMedium),
                const SizedBox(height: AppSpacing.grid),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: _skills
                      .map(
                        (s) => Chip(
                          label: Text(s),
                          backgroundColor: scheme.surfaceContainerHighest,
                        ),
                      )
                      .toList(),
                ),
                const SizedBox(height: AppSpacing.grid),
                Text(
                  'From your remade resume · skills are not interviewed',
                  style: type.bodySmall?.copyWith(color: colors.muted),
                ),
                const SizedBox(height: AppSpacing.grid * 3),
                FilledButton(
                  onPressed: _saving ? null : _save,
                  child: _saving
                      ? SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: scheme.onPrimary,
                          ),
                        )
                      : const Text('Looks good — continue'),
                ),
              ],
            ),
    );
  }
}

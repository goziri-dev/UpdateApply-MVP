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
  final _expSummaries = <TextEditingController>[];
  final _projSummaries = <TextEditingController>[];

  Map<String, dynamic> _data = {};
  List<Map<String, dynamic>> _experience = [];
  List<Map<String, dynamic>> _projects = [];
  List<String> _skills = [];
  bool _loading = true;
  bool _saving = false;

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
    for (final c in _expSummaries) {
      c.dispose();
    }
    for (final c in _projSummaries) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final res = await onboardingService.getProfile();
      final data = Map<String, dynamic>.from((res['data'] as Map?) ?? const {});
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

      for (final c in _expSummaries) {
        c.dispose();
      }
      for (final c in _projSummaries) {
        c.dispose();
      }
      _expSummaries
        ..clear()
        ..addAll(
          experience.map(
            (e) => TextEditingController(text: '${e['summary'] ?? ''}'),
          ),
        );
      _projSummaries
        ..clear()
        ..addAll(
          projects.map(
            (e) => TextEditingController(text: '${e['summary'] ?? ''}'),
          ),
        );

      _name.text = '${basics['name'] ?? ''}';
      _email.text = '${basics['email'] ?? ''}';
      _location.text = '${basics['location'] ?? ''}';
      final links = basics['links'];
      _links.text = links is List ? links.join(' · ') : '${links ?? ''}';

      setState(() {
        _data = data;
        _experience = experience;
        _projects = projects;
        _skills = skills;
        _loading = false;
      });
    } on DioException catch (e) {
      setOnboardingError(_dioMessage(e));
      setState(() => _loading = false);
    } on Object catch (e) {
      setOnboardingError(e.toString());
      setState(() => _loading = false);
    }
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
        });
      }
      final projects = <Map<String, dynamic>>[];
      for (var i = 0; i < _projects.length; i++) {
        projects.add({
          ..._projects[i],
          'summary': _projSummaries[i].text.trim(),
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
        'experience': experience,
        'projects': projects,
      };
      await onboardingService.updateProfile(payload);
      if (!mounted) return;
      context.go('/onboarding/ready');
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
    return e.message ?? 'Save failed';
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
      caption: 'Check anything that looks off',
      onBack: () => context.go('/onboarding/interview'),
      child: _loading
          ? const Padding(
              padding: EdgeInsets.only(top: 48),
              child: Center(child: CircularProgressIndicator()),
            )
          : Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text('Review your profile', style: type.headlineMedium),
                const SizedBox(height: AppSpacing.grid * 1.5),
                Text(
                  'Correct anything we got wrong. Skills are stored from your '
                  "resume — we don't ask about them in the chat.",
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
                  'Extracted from your resume · not covered in chat',
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

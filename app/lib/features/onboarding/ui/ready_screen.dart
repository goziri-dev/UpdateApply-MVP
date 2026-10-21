import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../state/onboarding_state.dart';
import '../widgets/onboarding_feedback.dart';
import '../widgets/onboarding_shell.dart';

class OnboardingReadyScreen extends StatefulWidget {
  const OnboardingReadyScreen({super.key});

  @override
  State<OnboardingReadyScreen> createState() => _OnboardingReadyScreenState();
}

class _OnboardingReadyScreenState extends State<OnboardingReadyScreen> {
  int _roles = 0;
  int _projects = 0;
  int _skills = 0;
  bool _loading = true;
  bool _completing = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final res = await onboardingService.getProfile();
      final data = Map<String, dynamic>.from((res['data'] as Map?) ?? const {});
      var skillCount = 0;
      for (final group in data['skills'] as List? ?? []) {
        if (group is String) {
          skillCount += 1;
        } else if (group is Map) {
          final keywords = group['keywords'] as List? ?? [];
          skillCount += keywords.isNotEmpty ? keywords.length : 1;
        }
      }
      setState(() {
        _roles = (data['experience'] as List? ?? []).length;
        _projects = (data['projects'] as List? ?? []).length;
        _skills = skillCount;
        _loading = false;
      });
    } on Object {
      setState(() => _loading = false);
    }
  }

  Future<void> _goTailor() async {
    setState(() => _completing = true);
    clearOnboardingFeedback();
    try {
      await onboardingService.complete();
      await refreshOnboardingGate(statusHint: 'complete');
      if (!mounted) return;
      context.go('/');
    } on DioException catch (e) {
      final detail = e.response?.data;
      setOnboardingError(
        detail is Map && detail['detail'] != null
            ? detail['detail'].toString()
            : (e.message ?? 'Could not complete onboarding'),
      );
    } on Object catch (e) {
      setOnboardingError(e.toString());
    } finally {
      if (mounted) setState(() => _completing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;
    final colors = context.appColors;

    return OnboardingShell(
      stepLabel: '5 / 5',
      caption: 'Ready to tailor to a job description',
      backEnabled: false,
      child: _loading
          ? const Padding(
              padding: EdgeInsets.only(top: 48),
              child: Center(child: CircularProgressIndicator()),
            )
          : Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Align(
                  alignment: Alignment.centerLeft,
                  child: Container(
                    width: 56,
                    height: 56,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: scheme.primary,
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Text(
                      'u+',
                      style: type.titleMedium?.copyWith(
                        color: scheme.onPrimary,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: AppSpacing.grid * 2.5),
                Text(
                  "Here's your profile — ready to tailor",
                  style: type.headlineMedium,
                ),
                const SizedBox(height: AppSpacing.grid * 1.5),
                Text(
                  'Onboarding is complete. Your career profile is the source of '
                  'truth for every tailored resume from here on.',
                  style: type.bodyMedium?.copyWith(
                    color: colors.muted,
                    height: 1.45,
                    fontWeight: FontWeight.w400,
                  ),
                ),
                const SizedBox(height: AppSpacing.grid * 3),
                Row(
                  children: [
                    Expanded(
                      child: _Stat(n: '$_roles', label: 'Roles covered'),
                    ),
                    Expanded(
                      child: _Stat(n: '$_projects', label: 'Projects covered'),
                    ),
                    Expanded(
                      child: _Stat(n: '$_skills', label: 'Skills stored'),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.grid * 2),
                const OnboardingFeedbackBanner(),
                DecoratedBox(
                  decoration: BoxDecoration(
                    color: scheme.primary.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(AppSpacing.grid * 2),
                    child: Text(
                      'Hard gate cleared — you can enter Tailor.',
                      style: type.bodyMedium?.copyWith(color: scheme.primary),
                    ),
                  ),
                ),
                const SizedBox(height: AppSpacing.grid * 3),
                FilledButton(
                  onPressed: _completing ? null : _goTailor,
                  child: _completing
                      ? SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: scheme.onPrimary,
                          ),
                        )
                      : const Text('Start tailoring'),
                ),
                const SizedBox(height: AppSpacing.grid),
                TextButton(
                  onPressed: () => context.go('/onboarding/review'),
                  child: const Text('Edit profile again'),
                ),
              ],
            ),
    );
  }
}

class _Stat extends StatelessWidget {
  const _Stat({required this.n, required this.label});

  final String n;
  final String label;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    return Column(
      children: [
        Text(n, style: type.headlineMedium),
        const SizedBox(height: 4),
        Text(
          label,
          textAlign: TextAlign.center,
          style: type.bodySmall?.copyWith(color: colors.muted),
        ),
      ],
    );
  }
}

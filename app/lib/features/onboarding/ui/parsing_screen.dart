import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../state/onboarding_state.dart';
import '../widgets/onboarding_shell.dart';

class OnboardingParsingScreen extends StatefulWidget {
  const OnboardingParsingScreen({super.key});

  @override
  State<OnboardingParsingScreen> createState() =>
      _OnboardingParsingScreenState();
}

class _OnboardingParsingScreenState extends State<OnboardingParsingScreen> {
  int _tick = 0;
  Timer? _timer;
  bool _failed = false;
  String? _error;

  static const _items = [
    'Basics (name, email, location, links)',
    'Education & certifications',
    'Work history',
    'Projects & skills',
  ];

  @override
  void initState() {
    super.initState();
    _start();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _start() async {
    clearOnboardingFeedback();
    _timer = Timer.periodic(const Duration(milliseconds: 700), (t) {
      if (!mounted) return;
      setState(() => _tick += 1);
      if (_tick >= 4) t.cancel();
    });

    try {
      await onboardingService.parse();
      // Let the checklist animation finish for UX parity with the prototype.
      while (_tick < 4) {
        await Future<void>.delayed(const Duration(milliseconds: 200));
        if (!mounted) return;
      }
      await Future<void>.delayed(const Duration(milliseconds: 400));
      if (!mounted) return;
      context.go('/onboarding/interview');
    } on DioException catch (e) {
      _timer?.cancel();
      setState(() {
        _failed = true;
        _error = _dioMessage(e);
      });
    } on Object catch (e) {
      _timer?.cancel();
      setState(() {
        _failed = true;
        _error = e.toString();
      });
    }
  }

  String _dioMessage(DioException e) {
    final detail = e.response?.data;
    if (detail is Map && detail['detail'] != null) {
      return detail['detail'].toString();
    }
    return e.message ?? 'Parsing failed';
  }

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;
    final colors = context.appColors;

    if (_failed) {
      return OnboardingShell(
        stepLabel: '2 / 5',
        caption: 'Reading your resume…',
        onBack: () => context.go('/onboarding/upload'),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text("We couldn't read that resume", style: type.headlineMedium),
            const SizedBox(height: AppSpacing.grid * 1.5),
            Text(
              'The PDF uploaded, but parsing failed. Try another export, or '
              're-upload a text-based PDF (not a scan).',
              style: type.bodyMedium?.copyWith(
                color: colors.muted,
                height: 1.45,
                fontWeight: FontWeight.w400,
              ),
            ),
            const SizedBox(height: AppSpacing.grid * 2),
            DecoratedBox(
              decoration: BoxDecoration(
                color: scheme.errorContainer,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Padding(
                padding: const EdgeInsets.all(AppSpacing.grid * 2),
                child: Text(
                  _error ?? 'Parsing error',
                  style: type.bodyMedium?.copyWith(color: scheme.error),
                ),
              ),
            ),
            const SizedBox(height: AppSpacing.grid * 3),
            FilledButton(
              onPressed: () => context.go('/onboarding/upload'),
              child: const Text('Try another PDF'),
            ),
          ],
        ),
      );
    }

    final active = _tick.clamp(0, _items.length - 1);

    return OnboardingShell(
      stepLabel: '2 / 5',
      caption: 'Reading your resume…',
      onBack: () => context.go('/onboarding/upload'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('Reading your resume', style: type.headlineMedium),
          const SizedBox(height: AppSpacing.grid * 1.5),
          Text(
            "We're extracting a structured profile. Interviews start once "
            'your experience list is ready — this usually takes a few seconds.',
            style: type.bodyMedium?.copyWith(
              color: colors.muted,
              height: 1.45,
              fontWeight: FontWeight.w400,
            ),
          ),
          const SizedBox(height: AppSpacing.grid * 3),
          DecoratedBox(
            decoration: BoxDecoration(
              color: scheme.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(16),
            ),
            child: Padding(
              padding: const EdgeInsets.all(AppSpacing.grid * 3),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    children: [
                      SizedBox(
                        width: 22,
                        height: 22,
                        child: CircularProgressIndicator(
                          strokeWidth: 2.5,
                          color: scheme.primary,
                        ),
                      ),
                      const SizedBox(width: AppSpacing.grid * 2),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('Parsing PDF', style: type.bodyLarge),
                            Text(
                              'Please keep this tab open',
                              style: type.bodySmall?.copyWith(
                                color: colors.muted,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.grid * 3),
                  ...List.generate(_items.length, (i) {
                    final done = i < _tick;
                    final isActive = i == active && _tick < _items.length;
                    return Padding(
                      padding: const EdgeInsets.only(bottom: AppSpacing.grid),
                      child: Row(
                        children: [
                          SizedBox(
                            width: 22,
                            child: Text(
                              done ? '✓' : (isActive ? '•' : ''),
                              style: type.bodyMedium?.copyWith(
                                color: done ? scheme.primary : colors.muted,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                          Expanded(
                            child: Text(
                              _items[i],
                              style: type.bodyMedium?.copyWith(
                                color: done || isActive
                                    ? scheme.onSurface
                                    : colors.muted,
                              ),
                            ),
                          ),
                        ],
                      ),
                    );
                  }),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

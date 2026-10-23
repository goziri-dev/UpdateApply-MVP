import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../../onboarding/state/onboarding_state.dart';
import '../../onboarding/widgets/onboarding_feedback.dart';
import '../../onboarding/widgets/onboarding_shell.dart';
import '../widgets/resume_preview.dart';

/// Post-review unlock: full resume preview + Download / Go to dashboard.
class ResumeRevealScreen extends StatefulWidget {
  const ResumeRevealScreen({super.key});

  @override
  State<ResumeRevealScreen> createState() => _ResumeRevealScreenState();
}

class _ResumeRevealScreenState extends State<ResumeRevealScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _unlock;
  late final Animation<double> _fade;
  late final Animation<Offset> _slide;
  late final Animation<double> _scale;

  bool _downloading = false;
  bool _goingHome = false;

  @override
  void initState() {
    super.initState();
    _unlock = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 520),
    );
    final curve = CurvedAnimation(parent: _unlock, curve: Curves.easeOutCubic);
    _fade = curve;
    _slide = Tween<Offset>(
      begin: const Offset(0, 0.04),
      end: Offset.zero,
    ).animate(curve);
    _scale = Tween<double>(begin: 0.97, end: 1).animate(curve);
    _unlock.forward();
  }

  @override
  void dispose() {
    _unlock.dispose();
    super.dispose();
  }

  Future<void> _download() async {
    setState(() => _downloading = true);
    clearOnboardingFeedback();
    try {
      await downloadResumePdf(context);
    } finally {
      if (mounted) setState(() => _downloading = false);
    }
  }

  Future<void> _goDashboard() async {
    setState(() => _goingHome = true);
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
            : (e.message ?? 'Could not open dashboard'),
      );
    } on Object catch (e) {
      setOnboardingError(e.toString());
    } finally {
      if (mounted) setState(() => _goingHome = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;
    final colors = context.appColors;
    final busy = _downloading || _goingHome;

    return OnboardingShell(
      stepLabel: '5 / 5',
      caption: 'Your remade resume',
      backEnabled: !busy,
      onBack: () => context.go('/onboarding/review'),
      child: FadeTransition(
        opacity: _fade,
        child: SlideTransition(
          position: _slide,
          child: ScaleTransition(
            scale: _scale,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Align(
                  alignment: Alignment.centerLeft,
                  child: Container(
                    width: 48,
                    height: 48,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: scheme.primary.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Icon(
                      Icons.auto_awesome,
                      color: scheme.primary,
                      size: 22,
                    ),
                  ),
                ),
                const SizedBox(height: AppSpacing.grid * 2),
                Text("Here's your resume", style: type.headlineMedium),
                const SizedBox(height: AppSpacing.grid * 1.5),
                Text(
                  'We turned your remade profile into a clean, ATS-friendly '
                  'resume. Download a PDF or open your dashboard — same '
                  'preview lives there as a mini card.',
                  style: type.bodyMedium?.copyWith(
                    color: colors.muted,
                    height: 1.45,
                    fontWeight: FontWeight.w400,
                  ),
                ),
                const SizedBox(height: AppSpacing.grid * 2),
                const OnboardingFeedbackBanner(),
                const Center(
                  child: ResumePreview(
                    mode: ResumePreviewMode.full,
                    viewTypePrefix: 'resume-reveal',
                    maxWidth: 520,
                  ),
                ),
                const SizedBox(height: AppSpacing.grid * 3),
                FilledButton(
                  onPressed: busy ? null : _download,
                  child: _downloading
                      ? SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: scheme.onPrimary,
                          ),
                        )
                      : const Text('Download PDF'),
                ),
                const SizedBox(height: AppSpacing.grid),
                OutlinedButton(
                  onPressed: busy ? null : _goDashboard,
                  child: _goingHome
                      ? SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: scheme.primary,
                          ),
                        )
                      : const Text('Go to dashboard'),
                ),
                const SizedBox(height: AppSpacing.grid),
                TextButton(
                  onPressed: busy
                      ? null
                      : () => context.go('/onboarding/review'),
                  child: const Text('Edit profile again'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

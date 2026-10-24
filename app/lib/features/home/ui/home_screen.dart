import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../../resume/widgets/resume_preview.dart';

/// Master resume + Tailor CTA — matches `prototypes/applications/` Home state.
///
/// Shell tabs already say Home; body leads with the resume composition, not a
/// redundant "Home" page title.
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;

    return ListView(
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.grid * 3,
        AppSpacing.grid * 5,
        AppSpacing.grid * 3,
        AppSpacing.grid * 6,
      ),
      children: [
        Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'YOUR RESUME',
                  style: type.bodySmall?.copyWith(
                    color: colors.label,
                    letterSpacing: 0.02 * 13,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: AppSpacing.grid * 1.5),
                ResumePreview(
                  mode: ResumePreviewMode.mini,
                  viewTypePrefix: 'resume-home-mini',
                  onTap: () => showResumePreviewModal(context),
                ),
                const SizedBox(height: AppSpacing.grid * 1.5),
                Text(
                  'Tap to enlarge or download',
                  style: type.bodySmall?.copyWith(
                    color: colors.muted,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(height: AppSpacing.grid * 2),
                Text(
                  'Paste a job description to generate a tailored resume '
                  'from your remade master profile.',
                  style: type.bodyMedium?.copyWith(
                    color: colors.muted,
                    height: 1.45,
                    fontWeight: FontWeight.w400,
                  ),
                ),
                const SizedBox(height: AppSpacing.grid * 2),
                FilledButton(
                  onPressed: () => context.push('/tailor'),
                  child: const Text('Tailor to a job description'),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

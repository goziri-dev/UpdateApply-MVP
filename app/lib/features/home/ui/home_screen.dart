import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../../resume/widgets/resume_preview.dart';

/// Master resume + Tailor CTA — matches `prototypes/applications/` Home state.
///
/// Shell tabs already say Home; body leads with the resume composition, not a
/// redundant "Home" page title. Edit master lives in the resume preview modal;
/// reset / re-onboard lives in Settings.
///
/// The shell mounts only the active branch (not IndexedStack), so this screen
/// — and its resume [HtmlElementView] — fully dispose when leaving Home.
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
                  'MASTER RESUME',
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
                  onTap: () =>
                      showResumePreviewModal(context, showEditMaster: true),
                ),
                const SizedBox(height: AppSpacing.grid * 1.5),
                Text(
                  'Tap to enlarge, download, or edit',
                  style: type.bodySmall?.copyWith(
                    color: colors.muted,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(height: AppSpacing.grid * 2),
                Text(
                  'Paste a job description to tailor your resume.',
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

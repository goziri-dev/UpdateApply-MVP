import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';

/// Soft “1 tailoring left” banner (prototype soft nudge).
class CreditsNudgeBanner extends StatelessWidget {
  const CreditsNudgeBanner({
    super.key,
    required this.onGetCredits,
    required this.onDismiss,
  });

  final VoidCallback onGetCredits;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final narrow = MediaQuery.sizeOf(context).width < 640;

    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: const Duration(milliseconds: 240),
      curve: const Cubic(0.22, 1, 0.36, 1),
      builder: (context, t, child) {
        return Opacity(
          opacity: t,
          child: Transform.translate(
            offset: Offset(0, 8 * (1 - t)),
            child: child,
          ),
        );
      },
      child: Container(
        margin: EdgeInsets.fromLTRB(
          AppSpacing.grid * (narrow ? 2 : 3),
          AppSpacing.grid * 2,
          AppSpacing.grid * (narrow ? 2 : 3),
          0,
        ),
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.grid * 2.5,
          vertical: AppSpacing.grid * 1.75,
        ),
        decoration: BoxDecoration(
          color: colors.warnBg,
          borderRadius: BorderRadius.circular(AppSpacing.markRadius),
        ),
        child: Flex(
          direction: narrow ? Axis.vertical : Axis.horizontal,
          crossAxisAlignment: narrow
              ? CrossAxisAlignment.stretch
              : CrossAxisAlignment.center,
          children: [
            Expanded(
              flex: narrow ? 0 : 1,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '1 tailoring left',
                    style: type.bodyMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                      color: colors.warnInk,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    'Top up so your next role isn’t blocked.',
                    style: type.bodySmall?.copyWith(
                      color: colors.muted,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
            SizedBox(
              height: narrow ? AppSpacing.grid * 1.5 : 0,
              width: narrow ? 0 : AppSpacing.grid * 2,
            ),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                FilledButton(
                  onPressed: onGetCredits,
                  style: FilledButton.styleFrom(
                    backgroundColor: Theme.of(context).colorScheme.onSurface,
                    foregroundColor: Theme.of(context).colorScheme.surface,
                    minimumSize: const Size(0, 40),
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    textStyle: type.bodySmall?.copyWith(
                      fontWeight: FontWeight.w600,
                      fontSize: 13,
                    ),
                  ),
                  child: const Text('Get credits'),
                ),
                const SizedBox(width: AppSpacing.grid * 1.5),
                TextButton(onPressed: onDismiss, child: const Text('Dismiss')),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

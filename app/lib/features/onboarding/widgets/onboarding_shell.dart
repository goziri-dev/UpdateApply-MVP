import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';

/// Shared chrome: Back + step indicator + left content / right abstract resume.
class OnboardingShell extends StatelessWidget {
  const OnboardingShell({
    super.key,
    required this.stepLabel,
    required this.caption,
    required this.child,
    this.onBack,
    this.backEnabled = true,
  });

  final String stepLabel;
  final String caption;
  final Widget child;
  final VoidCallback? onBack;
  final bool backEnabled;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;
    final colors = context.appColors;
    final wide = MediaQuery.sizeOf(context).width >= 900;

    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.grid * 3,
                vertical: AppSpacing.grid * 2,
              ),
              child: Row(
                children: [
                  TextButton(
                    onPressed: backEnabled
                        ? (onBack ?? () => context.pop())
                        : null,
                    style: TextButton.styleFrom(
                      foregroundColor: scheme.onSurface,
                      disabledForegroundColor: colors.muted.withValues(
                        alpha: 0.4,
                      ),
                    ),
                    child: const Text('← Back'),
                  ),
                  const Spacer(),
                  Text(
                    stepLabel,
                    style: type.bodySmall?.copyWith(color: colors.muted),
                  ),
                ],
              ),
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.grid * 3,
                ),
                child: wide
                    ? Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(
                            flex: 5,
                            child: SingleChildScrollView(
                              padding: const EdgeInsets.only(
                                bottom: AppSpacing.grid * 4,
                                right: AppSpacing.grid * 3,
                              ),
                              child: ConstrainedBox(
                                constraints: const BoxConstraints(
                                  maxWidth: 520,
                                ),
                                child: child,
                              ),
                            ),
                          ),
                          Expanded(
                            flex: 4,
                            child: _IllusPanel(caption: caption),
                          ),
                        ],
                      )
                    : SingleChildScrollView(
                        padding: const EdgeInsets.only(
                          bottom: AppSpacing.grid * 4,
                        ),
                        child: child,
                      ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _IllusPanel extends StatelessWidget {
  const _IllusPanel({required this.caption});

  final String caption;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final colors = context.appColors;

    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.grid * 2),
      child: Column(
        children: [
          Expanded(
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(
                  maxWidth: 320,
                  maxHeight: 420,
                ),
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    color: scheme.surfaceContainerHighest,
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(AppSpacing.grid * 3),
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: colors.oauthBorder),
                      ),
                      child: Padding(
                        padding: const EdgeInsets.all(AppSpacing.grid * 2.5),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Row(
                              children: [
                                Container(
                                  width: 40,
                                  height: 40,
                                  decoration: BoxDecoration(
                                    color: scheme.primary.withValues(
                                      alpha: 0.15,
                                    ),
                                    borderRadius: BorderRadius.circular(20),
                                  ),
                                ),
                                const SizedBox(width: AppSpacing.grid * 1.5),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      _Bar(
                                        widthFactor: 0.85,
                                        color: colors.oauthBorder,
                                      ),
                                      const SizedBox(height: 8),
                                      _Bar(
                                        widthFactor: 0.55,
                                        color: colors.oauthBorder,
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: AppSpacing.grid * 3),
                            _Bar(widthFactor: 0.7, color: colors.oauthBorder),
                            const SizedBox(height: 8),
                            _Bar(widthFactor: 1, color: colors.oauthBorder),
                            const SizedBox(height: 8),
                            _Bar(widthFactor: 0.45, color: colors.oauthBorder),
                            const SizedBox(height: AppSpacing.grid * 3),
                            Row(
                              children: [
                                Expanded(
                                  child: _Tile(
                                    color: scheme.primary.withValues(
                                      alpha: 0.12,
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: _Tile(
                                    color: scheme.primary.withValues(
                                      alpha: 0.18,
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: _Tile(
                                    color: scheme.primary.withValues(
                                      alpha: 0.1,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: AppSpacing.grid * 3),
                            _Bar(widthFactor: 0.65, color: colors.oauthBorder),
                            const SizedBox(height: 8),
                            _Bar(widthFactor: 1, color: colors.oauthBorder),
                            const SizedBox(height: 8),
                            _Bar(widthFactor: 0.8, color: colors.oauthBorder),
                            const SizedBox(height: 8),
                            _Bar(widthFactor: 0.4, color: colors.oauthBorder),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.grid * 3),
            child: Text(
              caption,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodySmall
                  ?.copyWith(color: colors.muted, fontWeight: FontWeight.w500),
            ),
          ),
        ],
      ),
    );
  }
}

class _Bar extends StatelessWidget {
  const _Bar({required this.widthFactor, required this.color});

  final double widthFactor;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return FractionallySizedBox(
      widthFactor: widthFactor,
      alignment: Alignment.centerLeft,
      child: Container(
        height: 10,
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(4),
        ),
      ),
    );
  }
}

class _Tile extends StatelessWidget {
  const _Tile({required this.color});

  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 36,
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(8),
      ),
    );
  }
}

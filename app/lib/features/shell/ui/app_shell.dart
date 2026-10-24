import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../../auth/widgets/auth_brand_mark.dart';
import '../widgets/shell_account_menu.dart';

/// Post-onboarding chrome: brand + Home | Jobs For You | Applications.
///
/// Tailor is intentionally not a shell tab — reached via CTAs only.
/// Account menu: Settings + Sign out. Job preferences lives under Settings.
class AppShell extends StatelessWidget {
  const AppShell({super.key, required this.navigationShell});

  final StatefulNavigationShell navigationShell;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;
    final colors = context.appColors;

    return Scaffold(
      backgroundColor: scheme.surface,
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Material(
            color: scheme.surface.withValues(alpha: 0.92),
            child: SafeArea(
              bottom: false,
              child: Container(
                constraints: const BoxConstraints(minHeight: 56),
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.grid * 3,
                  vertical: AppSpacing.grid * 1.5,
                ),
                decoration: BoxDecoration(
                  border: Border(
                    bottom: BorderSide(color: scheme.onSurface, width: 1.5),
                  ),
                ),
                // Equal side slots keep Home | Applications truly centered
                // once the account menu sits on the right.
                child: Row(
                  children: [
                    Expanded(
                      child: Align(
                        alignment: Alignment.centerLeft,
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Transform.scale(
                              scale: 32 / 44,
                              child: const AuthBrandMark(),
                            ),
                            const SizedBox(width: AppSpacing.grid),
                            Text(
                              'UpdateApply',
                              style: type.bodyLarge?.copyWith(
                                fontWeight: FontWeight.w700,
                                letterSpacing: -0.02 * 15,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    _ShellTabs(
                      index: navigationShell.currentIndex,
                      onSelect: (i) => navigationShell.goBranch(
                        i,
                        initialLocation: i == navigationShell.currentIndex,
                      ),
                      muted: colors.muted,
                      ink: scheme.onSurface,
                      accent: scheme.primary,
                    ),
                    const Expanded(
                      child: Align(
                        alignment: Alignment.centerRight,
                        child: ShellAccountMenu(),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
          Expanded(child: navigationShell),
        ],
      ),
    );
  }
}

class _ShellTabs extends StatelessWidget {
  const _ShellTabs({
    required this.index,
    required this.onSelect,
    required this.muted,
    required this.ink,
    required this.accent,
  });

  final int index;
  final ValueChanged<int> onSelect;
  final Color muted;
  final Color ink;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;

    Widget tab(String label, int i) {
      final selected = index == i;
      return TextButton(
        onPressed: () => onSelect(i),
        style: TextButton.styleFrom(
          foregroundColor: selected ? ink : muted,
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.grid * 1.5,
            vertical: AppSpacing.grid,
          ),
          minimumSize: Size.zero,
          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              label,
              style: type.bodySmall?.copyWith(
                fontSize: 13,
                fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                color: selected ? ink : muted,
              ),
            ),
            const SizedBox(height: 4),
            AnimatedContainer(
              duration: const Duration(milliseconds: 180),
              curve: Curves.easeOut,
              height: 2,
              width: selected ? 28 : 0,
              color: selected ? accent : Colors.transparent,
            ),
          ],
        ),
      );
    }

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        tab('Home', 0),
        const SizedBox(width: AppSpacing.grid * 0.5),
        tab('Jobs For You', 1),
        const SizedBox(width: AppSpacing.grid * 0.5),
        tab('Applications', 2),
      ],
    );
  }
}

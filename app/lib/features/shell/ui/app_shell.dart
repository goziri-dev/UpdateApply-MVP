import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../../auth/widgets/auth_brand_mark.dart';
import '../widgets/shell_account_menu.dart';
import '../widgets/shell_credits_cta.dart';

/// Below this width, primary nav collapses into a hamburger [MenuAnchor]
/// (mobile web chrome — not a native bottom tab bar).
const double _kShellCompactBreakpoint = 840;

/// Show brand wordmark beside the mark when the top tab row has room.
const double _kShellWordmarkBreakpoint = 980;

/// Post-onboarding chrome: brand + Home | Jobs For You | Applications.
///
/// Tailor is intentionally not a shell tab — reached via CTAs only.
/// Floating credits CTA + account menu (Settings, Sign out). Full plans UI is `/credits`.
class AppShell extends StatelessWidget {
  const AppShell({super.key, required this.navigationShell});

  final StatefulNavigationShell navigationShell;

  void _goBranch(int i) {
    navigationShell.goBranch(
      i,
      initialLocation: i == navigationShell.currentIndex,
    );
  }

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;
    final colors = context.appColors;
    final media = MediaQuery.of(context);
    final compact = media.size.width < _kShellCompactBreakpoint;
    final creditsBottom = media.padding.bottom + AppSpacing.grid * 2;

    return Scaffold(
      backgroundColor: scheme.surface,
      body: Stack(
        children: [
          Column(
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
                    child: compact
                        ? Row(
                            children: [
                              Transform.scale(
                                scale: 32 / 44,
                                child: const AuthBrandMark(),
                              ),
                              const Spacer(),
                              _ShellNavMenu(
                                index: navigationShell.currentIndex,
                                onSelect: _goBranch,
                                muted: colors.muted,
                                ink: scheme.onSurface,
                              ),
                              const SizedBox(width: AppSpacing.grid),
                              const ShellAccountMenu(),
                            ],
                          )
                        : Row(
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
                                      if (media.size.width >=
                                          _kShellWordmarkBreakpoint) ...[
                                        const SizedBox(width: AppSpacing.grid),
                                        Text(
                                          'UpdateApply',
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                          style: type.bodyLarge?.copyWith(
                                            fontWeight: FontWeight.w700,
                                            letterSpacing: -0.02 * 15,
                                          ),
                                        ),
                                      ],
                                    ],
                                  ),
                                ),
                              ),
                              _ShellTabs(
                                index: navigationShell.currentIndex,
                                onSelect: _goBranch,
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
          // Floating credits pill — `/credits` is outside this shell so the
          // CTA naturally disappears there.
          Positioned(
            right: AppSpacing.grid * 2,
            bottom: creditsBottom,
            child: const ShellCreditsCta(),
          ),
        ],
      ),
    );
  }
}

/// Compact overflow menu for primary shell destinations (mobile web).
class _ShellNavMenu extends StatelessWidget {
  const _ShellNavMenu({
    required this.index,
    required this.onSelect,
    required this.muted,
    required this.ink,
  });

  final int index;
  final ValueChanged<int> onSelect;
  final Color muted;
  final Color ink;

  static const _labels = ['Home', 'Jobs For You', 'Applications'];

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;

    return MenuAnchor(
      alignmentOffset: const Offset(0, AppSpacing.grid),
      style: MenuStyle(
        backgroundColor: WidgetStatePropertyAll(scheme.surface),
        shape: WidgetStatePropertyAll(
          RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppSpacing.markRadius),
            side: BorderSide(color: scheme.outlineVariant),
          ),
        ),
        padding: const WidgetStatePropertyAll(
          EdgeInsets.symmetric(vertical: AppSpacing.grid),
        ),
      ),
      menuChildren: [
        for (var i = 0; i < _labels.length; i++)
          MenuItemButton(
            onPressed: () => onSelect(i),
            child: Text(
              _labels[i],
              style: type.bodyMedium?.copyWith(
                fontWeight: i == index ? FontWeight.w700 : FontWeight.w600,
                color: i == index ? ink : muted,
              ),
            ),
          ),
      ],
      builder: (context, controller, child) {
        return IconButton(
          tooltip: 'Menu',
          onPressed: () {
            if (controller.isOpen) {
              controller.close();
            } else {
              controller.open();
            }
          },
          style: IconButton.styleFrom(
            foregroundColor: ink,
            minimumSize: const Size(40, 40),
            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
          ),
          icon: const Icon(Icons.menu),
        );
      },
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
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
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

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          tab('Home', 0),
          const SizedBox(width: AppSpacing.grid * 0.5),
          tab('Jobs For You', 1),
          const SizedBox(width: AppSpacing.grid * 0.5),
          tab('Applications', 2),
        ],
      ),
    );
  }
}

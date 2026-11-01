import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../../auth/state/auth_state.dart';

enum ShellAccountAction { credits, settings, jobTargets, signOut }

/// Display label for the signed-in account (email, else id).
String shellAccountLabel() {
  final user = authRepository.service.currentUser;
  final email = user?.email?.trim();
  if (email != null && email.isNotEmpty) return email;
  return user?.id ?? 'Signed in';
}

Future<void> handleShellAccountAction(
  BuildContext context,
  ShellAccountAction action,
) async {
  switch (action) {
    case ShellAccountAction.credits:
      context.push('/credits');
    case ShellAccountAction.settings:
      context.push('/settings');
    case ShellAccountAction.jobTargets:
      context.push('/settings/match-preferences');
    case ShellAccountAction.signOut:
      await signOut();
  }
}

/// Account destinations for [MenuAnchor] (mobile hamburger).
///
/// Caller should place a [Divider] before this section when mixed with nav.
List<Widget> shellAccountMenuChildren(BuildContext context) {
  final type = Theme.of(context).textTheme;
  final colors = context.appColors;
  final label = shellAccountLabel();

  TextStyle itemStyle() =>
      type.bodyMedium?.copyWith(fontWeight: FontWeight.w600) ??
      const TextStyle(fontWeight: FontWeight.w600);

  return [
    MenuItemButton(
      onPressed: null,
      child: Text(
        label,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: type.bodySmall?.copyWith(
          color: colors.muted,
          fontWeight: FontWeight.w500,
        ),
      ),
    ),
    MenuItemButton(
      onPressed: () =>
          handleShellAccountAction(context, ShellAccountAction.credits),
      child: Text('Credits', style: itemStyle()),
    ),
    MenuItemButton(
      onPressed: () =>
          handleShellAccountAction(context, ShellAccountAction.jobTargets),
      child: Text('Job preferences', style: itemStyle()),
    ),
    MenuItemButton(
      onPressed: () =>
          handleShellAccountAction(context, ShellAccountAction.settings),
      child: Text('Settings', style: itemStyle()),
    ),
    MenuItemButton(
      onPressed: () =>
          handleShellAccountAction(context, ShellAccountAction.signOut),
      child: Text('Sign out', style: itemStyle()),
    ),
  ];
}

/// Compact account control for the shell header (desktop ≥840px).
class ShellAccountMenu extends StatelessWidget {
  const ShellAccountMenu({super.key});

  @override
  Widget build(BuildContext context) {
    final label = shellAccountLabel();
    final initial = _initialFor(label);
    final type = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;
    final colors = context.appColors;

    return PopupMenuButton<ShellAccountAction>(
      tooltip: 'Account',
      offset: const Offset(0, AppSpacing.grid),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppSpacing.markRadius),
        side: BorderSide(color: scheme.outlineVariant),
      ),
      color: scheme.surface,
      onSelected: (action) => handleShellAccountAction(context, action),
      itemBuilder: (context) => [
        PopupMenuItem<ShellAccountAction>(
          enabled: false,
          height: 40,
          child: Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: type.bodySmall?.copyWith(
              color: colors.muted,
              fontWeight: FontWeight.w500,
            ),
          ),
        ),
        const PopupMenuDivider(height: 1),
        PopupMenuItem<ShellAccountAction>(
          value: ShellAccountAction.credits,
          child: Text(
            'Credits',
            style: type.bodyMedium?.copyWith(fontWeight: FontWeight.w600),
          ),
        ),
        PopupMenuItem<ShellAccountAction>(
          value: ShellAccountAction.jobTargets,
          child: Text(
            'Job preferences',
            style: type.bodyMedium?.copyWith(fontWeight: FontWeight.w600),
          ),
        ),
        PopupMenuItem<ShellAccountAction>(
          value: ShellAccountAction.settings,
          child: Text(
            'Settings',
            style: type.bodyMedium?.copyWith(fontWeight: FontWeight.w600),
          ),
        ),
        PopupMenuItem<ShellAccountAction>(
          value: ShellAccountAction.signOut,
          child: Text(
            'Sign out',
            style: type.bodyMedium?.copyWith(fontWeight: FontWeight.w600),
          ),
        ),
      ],
      child: Semantics(
        button: true,
        label: 'Account menu',
        child: Container(
          width: 36,
          height: 36,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: scheme.surfaceContainerHighest,
            borderRadius: BorderRadius.circular(AppSpacing.markRadius),
            border: Border.all(color: scheme.outlineVariant),
          ),
          child: Text(
            initial,
            style: type.bodyMedium?.copyWith(
              fontWeight: FontWeight.w700,
              color: scheme.primary,
            ),
          ),
        ),
      ),
    );
  }

  static String _initialFor(String label) {
    final trimmed = label.trim();
    if (trimmed.isEmpty) return '?';
    return trimmed.substring(0, 1).toUpperCase();
  }
}

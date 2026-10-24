import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../../auth/state/auth_state.dart';

enum _AccountMenuAction { settings, jobTargets, signOut }

/// Compact account control for the shell header (email, Settings, Sign out).
class ShellAccountMenu extends StatelessWidget {
  const ShellAccountMenu({super.key});

  @override
  Widget build(BuildContext context) {
    final user = authRepository.service.currentUser;
    final email = user?.email?.trim();
    final label = (email != null && email.isNotEmpty)
        ? email
        : (user?.id ?? 'Signed in');
    final initial = _initialFor(label);
    final type = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;
    final colors = context.appColors;

    return PopupMenuButton<_AccountMenuAction>(
      tooltip: 'Account',
      offset: const Offset(0, AppSpacing.grid),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppSpacing.markRadius),
        side: BorderSide(color: scheme.outlineVariant),
      ),
      color: scheme.surface,
      onSelected: (action) async {
        switch (action) {
          case _AccountMenuAction.settings:
            context.push('/settings');
          case _AccountMenuAction.jobTargets:
            context.push('/settings/match-preferences');
          case _AccountMenuAction.signOut:
            await signOut();
        }
      },
      itemBuilder: (context) => [
        PopupMenuItem<_AccountMenuAction>(
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
        PopupMenuItem<_AccountMenuAction>(
          value: _AccountMenuAction.jobTargets,
          child: Text(
            'Job preferences',
            style: type.bodyMedium?.copyWith(fontWeight: FontWeight.w600),
          ),
        ),
        PopupMenuItem<_AccountMenuAction>(
          value: _AccountMenuAction.settings,
          child: Text(
            'Settings',
            style: type.bodyMedium?.copyWith(fontWeight: FontWeight.w600),
          ),
        ),
        PopupMenuItem<_AccountMenuAction>(
          value: _AccountMenuAction.signOut,
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

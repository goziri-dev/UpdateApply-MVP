import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import 'auth_header.dart';

class AuthModeSwitch extends StatelessWidget {
  const AuthModeSwitch({super.key, required this.mode, required this.onToggle});

  final AuthScreenMode mode;
  final VoidCallback onToggle;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final (prefix, action) = switch (mode) {
      AuthScreenMode.signIn => ("Don't have an account?", 'Sign up'),
      AuthScreenMode.signUp => ('Already have an account?', 'Sign in'),
      AuthScreenMode.resetPassword => ('Remembered it?', 'Sign in'),
    };

    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.grid * 2.5),
      child: Wrap(
        alignment: WrapAlignment.center,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          Text(prefix, style: type.bodyMedium),
          TextButton(
            onPressed: onToggle,
            style: TextButton.styleFrom(
              padding: const EdgeInsets.symmetric(horizontal: 6),
              minimumSize: Size.zero,
              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              foregroundColor: colors.link,
            ),
            child: Text(action),
          ),
        ],
      ),
    );
  }
}

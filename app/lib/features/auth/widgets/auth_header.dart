import 'package:flutter/material.dart';

import '../../../core/theme/app_theme.dart';

enum AuthScreenMode { signIn, signUp, resetPassword }

extension AuthScreenModeCopy on AuthScreenMode {
  String get headline => switch (this) {
    AuthScreenMode.signIn => 'Hello again',
    AuthScreenMode.signUp => 'Create your account',
    AuthScreenMode.resetPassword => 'Reset password',
  };

  String get subtitle => switch (this) {
    AuthScreenMode.signIn => 'Sign in to continue',
    AuthScreenMode.signUp => 'Sign up to start tailoring',
    AuthScreenMode.resetPassword => "We'll email you a reset link",
  };
}

class AuthHeader extends StatelessWidget {
  const AuthHeader({super.key, required this.mode});

  final AuthScreenMode mode;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;

    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.grid * 3.5),
      child: Column(
        children: [
          Text(
            mode.headline,
            textAlign: TextAlign.center,
            style: type.headlineMedium,
          ),
          const SizedBox(height: AppSpacing.grid),
          Text(
            mode.subtitle,
            textAlign: TextAlign.center,
            style: type.titleMedium,
          ),
        ],
      ),
    );
  }
}

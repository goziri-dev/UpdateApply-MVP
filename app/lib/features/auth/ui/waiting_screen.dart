import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../state/auth_state.dart';

/// Signed-in but not on ``app_allowlist`` — private beta blocked state.
class WaitingScreen extends StatelessWidget {
  const WaitingScreen({super.key});

  static final _waitlistUri = Uri.parse('https://updateapply.com');

  Future<void> _openWaitlist() async {
    await launchUrl(_waitlistUri, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final scheme = Theme.of(context).colorScheme;

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Padding(
              padding: const EdgeInsets.all(AppSpacing.grid * 3),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'UpdateApply',
                    textAlign: TextAlign.center,
                    style: type.headlineMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: AppSpacing.grid * 2),
                  Text(
                    'Private beta',
                    textAlign: TextAlign.center,
                    style: type.titleLarge,
                  ),
                  const SizedBox(height: AppSpacing.grid * 1.5),
                  Text(
                    "You're signed in, but this account isn't approved yet. "
                    'Join the waitlist on the website — waitlist signup does '
                    'not grant access by itself. Favour will email you when '
                    "you're in.",
                    textAlign: TextAlign.center,
                    style: type.bodyMedium?.copyWith(
                      color: colors.muted,
                      height: 1.45,
                    ),
                  ),
                  const SizedBox(height: AppSpacing.grid * 3),
                  FilledButton(
                    onPressed: _openWaitlist,
                    child: const Text('Open waitlist'),
                  ),
                  const SizedBox(height: AppSpacing.grid * 1.5),
                  TextButton(
                    onPressed: () => signOut(),
                    child: Text(
                      'Sign out',
                      style: TextStyle(color: scheme.onSurface),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

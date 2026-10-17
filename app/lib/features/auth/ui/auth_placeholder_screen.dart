import 'package:flutter/material.dart';

import '../../../core/config/app_env.dart';

/// Router placeholder until Favour approves `prototypes/auth/` and we implement UI.
class AuthPlaceholderScreen extends StatelessWidget {
  const AuthPlaceholderScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('UpdateApply', style: theme.textTheme.headlineMedium),
              const SizedBox(height: 12),
              Text(
                'Auth UI pending prototype approval',
                style: theme.textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              Text(
                'Open prototypes/auth/index.html to review sign-in / sign-up. '
                'OAuth: Google, GitHub, Notion (AuthService / AuthRepository).',
                style: theme.textTheme.bodyMedium,
              ),
              const SizedBox(height: 16),
              Text(
                AppEnv.supabaseConfigured
                    ? 'Supabase client: configured'
                    : 'Supabase client: missing SUPABASE_URL / SUPABASE_ANON_KEY '
                          '(use --dart-define-from-file=.env)',
                style: theme.textTheme.bodySmall,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

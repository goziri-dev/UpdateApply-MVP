import 'package:flutter/material.dart';
import 'package:signals/signals_flutter.dart';

import '../../../core/theme/app_theme.dart';
import '../services/auth_service.dart';
import '../state/auth_state.dart';
import 'auth_oauth_icons.dart';

class AuthOAuthStack extends StatelessWidget {
  const AuthOAuthStack({super.key});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: AppSpacing.grid * 2.5),
          child: Text(
            'or',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
        ),
        const _OAuthButton(
          provider: AuthOAuthProvider.google,
          busyTarget: AuthBusyTarget.google,
          label: 'Continue with Google',
          icon: null,
        ),
        const SizedBox(height: AppSpacing.grid * 1.25),
        const _OAuthButton(
          provider: AuthOAuthProvider.github,
          busyTarget: AuthBusyTarget.github,
          label: 'Continue with GitHub',
          icon: null,
        ),
        const SizedBox(height: AppSpacing.grid * 1.25),
        const _OAuthButton(
          provider: AuthOAuthProvider.notion,
          busyTarget: AuthBusyTarget.notion,
          label: 'Continue with Notion',
          icon: null,
        ),
      ],
    );
  }
}

class _OAuthButton extends StatelessWidget {
  const _OAuthButton({
    required this.provider,
    required this.busyTarget,
    required this.label,
    required this.icon,
  });

  final AuthOAuthProvider provider;
  final AuthBusyTarget busyTarget;
  final String label;
  final Widget? icon;

  Widget _iconFor(Color ink) {
    return switch (provider) {
      AuthOAuthProvider.google => AuthOAuthIcons.google(),
      AuthOAuthProvider.github => AuthOAuthIcons.github(color: ink),
      AuthOAuthProvider.notion => AuthOAuthIcons.notion(color: ink),
    };
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final type = Theme.of(context).textTheme;

    return SignalBuilder(
      builder: (context) {
        final busy = authBusy.value;
        final isLoading = busy == busyTarget;
        final disabled = busy != AuthBusyTarget.idle;

        return SizedBox(
          width: double.infinity,
          height: AppSpacing.controlHeight,
          child: OutlinedButton(
            onPressed: disabled ? null : () => continueWithOAuth(provider),
            style: OutlinedButton.styleFrom(
              backgroundColor: scheme.surfaceContainerHighest,
              foregroundColor: scheme.onSurface,
              disabledBackgroundColor: scheme.surfaceContainerHighest
                  .withValues(alpha: 0.7),
              side: BorderSide(color: scheme.outline),
              shape: const StadiumBorder(),
              textStyle: type.labelLarge,
            ),
            child: isLoading
                ? Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: scheme.onSurface,
                        ),
                      ),
                      const SizedBox(width: AppSpacing.grid * 1.25),
                      Text('Connecting…', style: type.labelLarge),
                    ],
                  )
                : Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      _iconFor(scheme.onSurface),
                      const SizedBox(width: AppSpacing.grid * 1.25),
                      Text(label),
                    ],
                  ),
          ),
        );
      },
    );
  }
}

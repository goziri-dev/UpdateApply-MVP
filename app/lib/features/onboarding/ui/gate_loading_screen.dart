import 'package:flutter/material.dart';
import 'package:signals_flutter/signals_flutter.dart';

import '../../../core/routing/auth_router_refresh.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../state/onboarding_state.dart';

/// Shown while onboarding status is unresolved (loading or API unreachable).
///
/// Prevents treating [OnboardingGate.unknown] as "needs onboarding," which
/// previously dumped already-complete users onto the upload screen when the
/// API was down.
class GateLoadingScreen extends StatelessWidget {
  const GateLoadingScreen({super.key, required this.authRefresh});

  final AuthRouterRefresh authRefresh;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;
    final colors = context.appColors;

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Padding(
              padding: const EdgeInsets.all(AppSpacing.grid * 3),
              child: SignalBuilder(
                builder: (context) {
                  final syncing = onboardingGateSyncing.value;
                  final error = onboardingGateSyncError.value;
                  final showError = error != null && !syncing;

                  return Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      if (!showError) ...[
                        Center(
                          child: SizedBox(
                            width: 28,
                            height: 28,
                            child: CircularProgressIndicator(
                              strokeWidth: 2.5,
                              color: scheme.primary,
                            ),
                          ),
                        ),
                        const SizedBox(height: AppSpacing.grid * 3),
                        Text(
                          'Checking your profile…',
                          textAlign: TextAlign.center,
                          style: type.titleMedium,
                        ),
                        const SizedBox(height: AppSpacing.grid),
                        Text(
                          'This only takes a moment.',
                          textAlign: TextAlign.center,
                          style: type.bodyMedium?.copyWith(color: colors.muted),
                        ),
                      ] else ...[
                        Text(
                          "We can't reach the server",
                          textAlign: TextAlign.center,
                          style: type.headlineSmall,
                        ),
                        const SizedBox(height: AppSpacing.grid * 1.5),
                        Text(
                          error,
                          textAlign: TextAlign.center,
                          style: type.bodyMedium?.copyWith(
                            color: colors.muted,
                            height: 1.45,
                          ),
                        ),
                        const SizedBox(height: AppSpacing.grid * 3),
                        FilledButton(
                          onPressed: () => authRefresh.retryGateSync(),
                          child: const Text('Retry'),
                        ),
                      ],
                    ],
                  );
                },
              ),
            ),
          ),
        ),
      ),
    );
  }
}

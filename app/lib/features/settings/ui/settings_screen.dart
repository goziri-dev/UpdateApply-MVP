import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:signals_flutter/signals_flutter.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../../onboarding/state/onboarding_state.dart';
import '../../onboarding/widgets/reset_onboarding.dart';
import '../../shell/widgets/shell_account_menu.dart';

/// Account / profile settings — reset only (Credits at `/credits`; Job preferences
/// via account menu → `/settings/match-preferences`).
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key, this.billingQuery});

  /// Legacy `/settings?billing=success|cancel` — redirected to `/credits`.
  final String? billingQuery;

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  @override
  void initState() {
    super.initState();
    final q = widget.billingQuery;
    if (q == 'success' || q == 'cancel') {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        context.go('/credits?billing=$q');
      });
    }
  }

  void _goBack(BuildContext context) {
    if (context.canPop()) {
      context.pop();
      return;
    }
    context.go('/');
  }

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final scheme = Theme.of(context).colorScheme;

    return Scaffold(
      backgroundColor: scheme.surface,
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.grid * 3,
            AppSpacing.grid * 2,
            AppSpacing.grid * 3,
            AppSpacing.grid * 6,
          ),
          children: [
            Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 420),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Align(
                      alignment: Alignment.centerLeft,
                      child: TextButton(
                        onPressed: () => _goBack(context),
                        style: TextButton.styleFrom(
                          foregroundColor: scheme.onSurface,
                          padding: EdgeInsets.zero,
                          minimumSize: Size.zero,
                          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        ),
                        child: const Text('← Home'),
                      ),
                    ),
                    const SizedBox(height: AppSpacing.grid * 2),
                    Text('Settings', style: type.headlineMedium),
                    const SizedBox(height: AppSpacing.grid),
                    Text(
                      'Account and profile controls for UpdateApply.',
                      style: type.bodyMedium?.copyWith(
                        color: colors.muted,
                        height: 1.45,
                        fontWeight: FontWeight.w400,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.grid * 4),
                    Text(
                      'ACCOUNT',
                      style: type.bodySmall?.copyWith(
                        color: colors.label,
                        letterSpacing: 0.02 * 13,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.grid * 1.5),
                    Text(
                      'Signed in as',
                      style: type.bodySmall?.copyWith(
                        color: colors.muted,
                        fontWeight: FontWeight.w400,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      shellAccountLabel(),
                      style: type.bodyLarge?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.grid * 4),
                    Text(
                      'PROFILE',
                      style: type.bodySmall?.copyWith(
                        color: colors.label,
                        letterSpacing: 0.02 * 13,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.grid * 1.5),
                    Text(
                      'Need a fresh start?',
                      style: type.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.grid),
                    Text(
                      'Start over with a new resume. Applications are kept.',
                      style: type.bodySmall?.copyWith(
                        color: colors.muted,
                        height: 1.45,
                        fontWeight: FontWeight.w400,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.grid * 2),
                    SignalBuilder(
                      builder: (context) {
                        final resetBusy = onboardingBusy.value;
                        return OutlinedButton(
                          onPressed: resetBusy
                              ? null
                              : () => confirmAndResetOnboarding(context),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: scheme.error,
                            side: BorderSide(
                              color: scheme.error.withValues(alpha: 0.45),
                            ),
                          ),
                          child: Text(
                            resetBusy
                                ? 'Resetting…'
                                : 'Reset profile & re-onboard',
                          ),
                        );
                      },
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:signals_flutter/signals_flutter.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../../billing/services/billing_service.dart';
import '../../billing/state/billing_state.dart';

/// Floating shell credits pill: remaining balance → `/credits`.
///
/// Mounted as an [AppShell] overlay (bottom-right), not in the app bar.
class ShellCreditsCta extends StatefulWidget {
  const ShellCreditsCta({super.key});

  @override
  State<ShellCreditsCta> createState() => _ShellCreditsCtaState();
}

class _ShellCreditsCtaState extends State<ShellCreditsCta> {
  @override
  void initState() {
    super.initState();
    // Defer so we don't write billing signals mid-build (hot reload / first frame).
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      refreshBillingBalance(service: BillingService());
    });
  }

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;
    final colors = context.appColors;

    return SignalBuilder(
      builder: (context) {
        final bal = billingBalance.value;
        final loading = billingBalanceLoading.value;
        final err = billingBalanceError.value;

        final String label;
        final Color bg;
        final Color fg;
        final String semantics;

        if (bal != null) {
          final n = bal.creditBalance;
          if (n <= 0) {
            label = '0 credits remaining · Top up?';
            bg = colors.dangerBg;
            fg = scheme.error;
            semantics = '0 credits remaining. Open credits and plans to top up';
          } else if (n == 1) {
            label = '1 credit remaining · Top up?';
            bg = colors.warnBg;
            fg = colors.warnInk;
            semantics = '1 credit remaining. Open credits and plans to top up';
          } else {
            label = '$n credits remaining · Top up?';
            bg = colors.accentSoft;
            fg = scheme.primary;
            semantics =
                '$n credits remaining. Open credits and plans to top up';
          }
        } else if (loading) {
          label = '… · Top up?';
          bg = scheme.surface;
          fg = colors.muted;
          semantics = 'Loading credits balance';
        } else if (err != null) {
          label = 'Credits · Top up?';
          bg = scheme.surface;
          fg = colors.muted;
          semantics = 'Could not load balance. Open credits and plans';
        } else {
          label = 'Credits · Top up?';
          bg = scheme.surface;
          fg = colors.muted;
          semantics = 'Open credits and plans';
        }

        return Semantics(
          button: true,
          label: semantics,
          child: Material(
            color: bg,
            elevation: 3,
            shadowColor: scheme.onSurface.withValues(alpha: 0.18),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(AppSpacing.pillRadius),
              side: BorderSide(color: scheme.primary.withValues(alpha: 0.18)),
            ),
            child: InkWell(
              borderRadius: BorderRadius.circular(AppSpacing.pillRadius),
              onTap: () => context.push('/credits'),
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.grid * 2,
                  vertical: AppSpacing.grid * 1.25,
                ),
                child: Text(
                  label,
                  style: type.bodySmall?.copyWith(
                    color: fg,
                    fontWeight: FontWeight.w600,
                    fontSize: 13,
                    height: 1.2,
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}

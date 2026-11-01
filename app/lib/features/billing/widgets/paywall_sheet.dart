import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../models/billing_plans.dart';
import '../services/billing_service.dart';
import '../state/billing_state.dart';
import 'billing_alert.dart';
import 'plan_comparison.dart';

/// Hard paywall: “Keep tailoring” + plan comparison (modal / sheet).
Future<void> showPaywallSheet(BuildContext context) {
  return showGeneralDialog<void>(
    context: context,
    barrierDismissible: true,
    barrierLabel: 'Close paywall',
    barrierColor: const Color(0xFF111111).withValues(alpha: 0.42),
    transitionDuration: const Duration(milliseconds: 220),
    pageBuilder: (context, animation, secondaryAnimation) {
      return const _PaywallDialog();
    },
    transitionBuilder: (context, animation, secondaryAnimation, child) {
      final curved = CurvedAnimation(
        parent: animation,
        curve: const Cubic(0.22, 1, 0.36, 1),
      );
      return FadeTransition(
        opacity: curved,
        child: SlideTransition(
          position: Tween<Offset>(
            begin: const Offset(0, 0.04),
            end: Offset.zero,
          ).animate(curved),
          child: child,
        ),
      );
    },
  );
}

class _PaywallDialog extends StatefulWidget {
  const _PaywallDialog();

  @override
  State<_PaywallDialog> createState() => _PaywallDialogState();
}

class _PaywallDialogState extends State<_PaywallDialog> {
  final _billing = BillingService();
  CheckoutPlan? _busyPlan;
  String? _error;

  Future<void> _checkout(CheckoutPlan plan) async {
    setState(() {
      _busyPlan = plan;
      _error = null;
    });
    try {
      final session = await _billing.createCheckout(plan.apiValue);
      final ok = await launchUrl(
        Uri.parse(session.checkoutUrl),
        mode: LaunchMode.externalApplication,
      );
      if (!ok && mounted) {
        setState(() => _error = 'Could not open Stripe Checkout.');
      }
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() => _error = messageFromBillingDio(e));
    } on Object catch (e) {
      if (!mounted) return;
      setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _busyPlan = null);
    }
  }

  void _onSelect(PlanCatalogEntry entry) {
    final plan = entry.checkoutPlan;
    if (plan == null) {
      Navigator.of(context).maybePop();
      return;
    }
    _checkout(plan);
  }

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final scheme = Theme.of(context).colorScheme;
    final wide = MediaQuery.sizeOf(context).width >= 800;
    final maxH = MediaQuery.sizeOf(context).height * 0.92;

    return SafeArea(
      child: Align(
        alignment: wide ? Alignment.center : Alignment.bottomCenter,
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.grid * 2),
          child: Material(
            color: scheme.surface,
            borderRadius: BorderRadius.circular(24),
            clipBehavior: Clip.antiAlias,
            child: ConstrainedBox(
              constraints: BoxConstraints(
                maxWidth: 1080,
                maxHeight: maxH.clamp(320, 900),
              ),
              child: SingleChildScrollView(
                padding: EdgeInsets.all(AppSpacing.grid * (wide ? 4 : 3)),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Keep tailoring',
                                style: type.displaySmall?.copyWith(
                                  fontSize: 28,
                                ),
                              ),
                              const SizedBox(height: AppSpacing.grid),
                              Text(
                                'You’re out of CV tailorings. Grab one now or unlock a monthly pack.',
                                style: type.bodyLarge?.copyWith(
                                  color: colors.muted,
                                  fontWeight: FontWeight.w500,
                                  height: 1.4,
                                ),
                              ),
                            ],
                          ),
                        ),
                        IconButton(
                          onPressed: () => Navigator.of(context).maybePop(),
                          style: IconButton.styleFrom(
                            backgroundColor: scheme.surfaceContainerHighest,
                          ),
                          icon: const Icon(Icons.close),
                          tooltip: 'Close',
                        ),
                      ],
                    ),
                    if (_error != null) ...[
                      const SizedBox(height: AppSpacing.grid * 2),
                      BillingAlert(
                        tone: BillingAlertTone.error,
                        message: _error!,
                        onDismiss: () => setState(() => _error = null),
                      ),
                    ],
                    const SizedBox(height: AppSpacing.grid * 3),
                    PlanComparison(
                      plans: kPaywallPlans,
                      busyPlan: _busyPlan,
                      compactFeatures: true,
                      onSelect: _onSelect,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

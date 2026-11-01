import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:signals_flutter/signals_flutter.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../models/billing_plans.dart';
import '../services/billing_service.dart';
import '../state/billing_state.dart';
import '../widgets/billing_alert.dart';
import '../widgets/plan_comparison.dart';

/// Credits & plans hub — Care.com-style comparison matching the approved prototype.
class CreditsScreen extends StatefulWidget {
  const CreditsScreen({super.key, this.billingQuery});

  /// From `/credits?billing=success|cancel` (or redirected settings return).
  final String? billingQuery;

  @override
  State<CreditsScreen> createState() => _CreditsScreenState();
}

class _CreditsScreenState extends State<CreditsScreen> {
  final _billing = BillingService();
  final _railKey = GlobalKey();

  CheckoutPlan? _busyPlan;
  bool _portalBusy = false;
  String? _actionError;
  String? _successBanner;
  String? _infoBanner;

  @override
  void initState() {
    super.initState();
    final q = widget.billingQuery;
    if (q == 'success') {
      _successBanner = 'Credits added. Ready to tailor.';
    } else if (q == 'cancel') {
      _infoBanner = 'Checkout cancelled. No charge was made.';
    }
    refreshBillingBalance(service: _billing);
  }

  Future<void> _checkout(CheckoutPlan plan) async {
    setState(() {
      _busyPlan = plan;
      _actionError = null;
    });
    try {
      final session = await _billing.createCheckout(plan.apiValue);
      final ok = await launchUrl(
        Uri.parse(session.checkoutUrl),
        mode: LaunchMode.externalApplication,
      );
      if (!ok && mounted) {
        setState(() => _actionError = 'Could not open Stripe Checkout.');
      }
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() => _actionError = messageFromBillingDio(e));
    } on Object catch (e) {
      if (!mounted) return;
      setState(() => _actionError = '$e');
    } finally {
      if (mounted) setState(() => _busyPlan = null);
    }
  }

  Future<void> _openPortal() async {
    setState(() {
      _portalBusy = true;
      _actionError = null;
    });
    try {
      final url = await _billing.createPortal();
      final ok = await launchUrl(
        Uri.parse(url),
        mode: LaunchMode.externalApplication,
      );
      if (!ok && mounted) {
        setState(() => _actionError = 'Could not open billing portal.');
      }
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() => _actionError = messageFromBillingDio(e));
    } on Object catch (e) {
      if (!mounted) return;
      setState(() => _actionError = '$e');
    } finally {
      if (mounted) setState(() => _portalBusy = false);
    }
  }

  void _onSelect(PlanCatalogEntry entry) {
    final plan = entry.checkoutPlan;
    if (plan == null) {
      if (context.canPop()) {
        context.pop();
      } else {
        context.go('/');
      }
      return;
    }
    _checkout(plan);
  }

  void _scrollToPlans() {
    final ctx = _railKey.currentContext;
    if (ctx != null) {
      Scrollable.ensureVisible(
        ctx,
        duration: const Duration(milliseconds: 280),
        curve: Curves.easeOut,
      );
    }
  }

  void _goBack() {
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
    final actionBusy = _busyPlan != null || _portalBusy;

    return Scaffold(
      backgroundColor: scheme.surface,
      body: SafeArea(
        child: SignalBuilder(
          builder: (context) {
            final bal = billingBalance.value;
            final loading = billingBalanceLoading.value;
            final balanceError = billingBalanceError.value;
            final emptyHub =
                !loading &&
                balanceError == null &&
                bal != null &&
                bal.creditBalance <= 0 &&
                widget.billingQuery != 'success';

            return ListView(
              padding: const EdgeInsets.fromLTRB(
                AppSpacing.grid * 3,
                AppSpacing.grid * 2,
                AppSpacing.grid * 3,
                AppSpacing.grid * 8,
              ),
              children: [
                Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 1120),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Align(
                          alignment: Alignment.centerLeft,
                          child: TextButton(
                            onPressed: _goBack,
                            style: TextButton.styleFrom(
                              foregroundColor: scheme.onSurface,
                              padding: EdgeInsets.zero,
                              minimumSize: Size.zero,
                              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                            ),
                            child: const Text('← Back'),
                          ),
                        ),
                        const SizedBox(height: AppSpacing.grid * 2),
                        if (_actionError != null) ...[
                          BillingAlert(
                            tone: BillingAlertTone.error,
                            message: _actionError!,
                            onDismiss: () =>
                                setState(() => _actionError = null),
                          ),
                          const SizedBox(height: AppSpacing.grid * 2),
                        ],
                        if (_successBanner != null) ...[
                          BillingAlert(
                            tone: BillingAlertTone.success,
                            message: _successBanner!,
                            actionLabel: 'Tailor now',
                            onAction: () => context.go('/tailor'),
                            onDismiss: () =>
                                setState(() => _successBanner = null),
                          ),
                          const SizedBox(height: AppSpacing.grid * 2),
                        ],
                        if (_infoBanner != null) ...[
                          BillingAlert(
                            tone: BillingAlertTone.error,
                            message: _infoBanner!,
                            onDismiss: () => setState(() => _infoBanner = null),
                          ),
                          const SizedBox(height: AppSpacing.grid * 2),
                        ],
                        if (emptyHub) ...[
                          Padding(
                            padding: const EdgeInsets.symmetric(
                              vertical: AppSpacing.grid * 4,
                            ),
                            child: Column(
                              children: [
                                Text(
                                  'No credits yet',
                                  style: type.headlineSmall?.copyWith(
                                    fontSize: 24,
                                  ),
                                  textAlign: TextAlign.center,
                                ),
                                const SizedBox(height: AppSpacing.grid),
                                Text(
                                  'Start with a single tailoring or a monthly plan.',
                                  textAlign: TextAlign.center,
                                  style: type.bodyMedium?.copyWith(
                                    color: colors.muted,
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                                const SizedBox(height: AppSpacing.grid * 3),
                                FilledButton(
                                  onPressed: _scrollToPlans,
                                  child: const Text('Choose a plan'),
                                ),
                              ],
                            ),
                          ),
                        ],
                        // Balance-only loading (plans are a static catalog).
                        if (balanceError != null && bal == null)
                          Padding(
                            padding: const EdgeInsets.only(
                              bottom: AppSpacing.grid * 2,
                            ),
                            child: BillingAlert(
                              tone: BillingAlertTone.error,
                              message: balanceError,
                              actionLabel: 'Retry',
                              onAction: () =>
                                  refreshBillingBalance(service: _billing),
                            ),
                          )
                        else if (bal != null) ...[
                          Align(
                            alignment: Alignment.center,
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 14,
                                vertical: 8,
                              ),
                              decoration: BoxDecoration(
                                color: bal.creditBalance <= 0
                                    ? colors.dangerBg
                                    : colors.accentSoft,
                                borderRadius: BorderRadius.circular(
                                  AppSpacing.pillRadius,
                                ),
                              ),
                              child: Text(
                                bal.creditBalance <= 0
                                    ? 'Balance · 0 credits'
                                    : 'Balance · ${bal.creditBalance} credit${bal.creditBalance == 1 ? '' : 's'}',
                                style: type.bodySmall?.copyWith(
                                  color: bal.creditBalance <= 0
                                      ? scheme.error
                                      : scheme.primary,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(height: AppSpacing.grid * 3),
                        ] else if (loading) ...[
                          Align(
                            alignment: Alignment.center,
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 14,
                                vertical: 8,
                              ),
                              decoration: BoxDecoration(
                                color: colors.accentSoft,
                                borderRadius: BorderRadius.circular(
                                  AppSpacing.pillRadius,
                                ),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Text(
                                    'Balance · ',
                                    style: type.bodySmall?.copyWith(
                                      color: scheme.primary,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                  Container(
                                    width: 64,
                                    height: 12,
                                    decoration: BoxDecoration(
                                      color: scheme.primary.withValues(
                                        alpha: 0.18,
                                      ),
                                      borderRadius: BorderRadius.circular(4),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                          const SizedBox(height: AppSpacing.grid * 3),
                        ],
                        KeyedSubtree(
                          key: _railKey,
                          child: PlanComparison(
                            plans: kCreditsHubPlans,
                            title: 'Choose your access',
                            subtitle: 'Free gets you started. Top up one at a time, or unlock a monthly pack when you’re applying hard.',
                            showSecondaryCheckout: true,
                            busyPlan: _busyPlan,
                            onSelect: (entry) {
                              if (actionBusy && entry.checkoutPlan != null) {
                                return;
                              }
                              _onSelect(entry);
                            },
                          ),
                        ),
                        const SizedBox(height: AppSpacing.grid * 3),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              'Already subscribed?',
                              style: type.bodySmall?.copyWith(
                                color: colors.muted,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                            const SizedBox(width: AppSpacing.grid * 2),
                            TextButton(
                              onPressed: actionBusy ? null : _openPortal,
                              child: Text(
                                _portalBusy ? 'Opening…' : 'Manage billing',
                              ),
                            ),
                          ],
                        ),
                        Center(
                          child: TextButton(
                            onPressed: loading
                                ? null
                                : () =>
                                      refreshBillingBalance(service: _billing),
                            child: const Text('Refresh balance'),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../models/billing_plans.dart';
import 'plan_card.dart';

/// Plan rail: 4-up on wide viewports; vertical stack everywhere else
/// (matches landing pricing discoverability — no hidden swipe-only cards).
class PlanComparison extends StatelessWidget {
  const PlanComparison({
    super.key,
    required this.plans,
    required this.onSelect,
    this.busyPlan,
    this.title,
    this.subtitle,
    this.showSecondaryCheckout = false,
    this.compactFeatures = false,
    this.minCardWidth = 240,
  });

  final List<PlanCatalogEntry> plans;
  final void Function(PlanCatalogEntry entry) onSelect;
  final CheckoutPlan? busyPlan;
  final String? title;
  final String? subtitle;
  final bool showSecondaryCheckout;
  final bool compactFeatures;

  /// Kept for call-site compatibility; unused now that mobile stacks vertically.
  final double minCardWidth;

  static const double _wideBreakpoint = 1100;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final wide = MediaQuery.sizeOf(context).width >= _wideBreakpoint;

    return DecoratedBox(
      decoration: BoxDecoration(
        color: colors.stage,
        borderRadius: BorderRadius.circular(AppSpacing.stageRadius),
      ),
      child: Padding(
        padding: EdgeInsets.fromLTRB(
          AppSpacing.grid * 3,
          AppSpacing.grid * (title != null ? 4 : 3),
          AppSpacing.grid * 3,
          AppSpacing.grid * 3,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (title != null) ...[
              Text(
                title!,
                textAlign: TextAlign.center,
                style: type.displaySmall?.copyWith(fontSize: wide ? null : 28),
              ),
              if (subtitle != null) ...[
                const SizedBox(height: AppSpacing.grid),
                Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 42 * 10),
                    child: Text(
                      subtitle!,
                      textAlign: TextAlign.center,
                      style: type.bodyLarge?.copyWith(
                        color: colors.muted,
                        fontWeight: FontWeight.w500,
                        height: 1.4,
                      ),
                    ),
                  ),
                ),
              ],
              const SizedBox(height: AppSpacing.grid * 4),
            ],
            if (wide)
              IntrinsicHeight(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    for (var i = 0; i < plans.length; i++) ...[
                      if (i > 0) const SizedBox(width: AppSpacing.grid * 2),
                      Expanded(child: _card(plans[i], pinFooter: true)),
                    ],
                  ],
                ),
              )
            else
              Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  for (var i = 0; i < plans.length; i++) ...[
                    if (i > 0) const SizedBox(height: AppSpacing.grid * 2),
                    _card(plans[i], pinFooter: false),
                  ],
                ],
              ),
          ],
        ),
      ),
    );
  }

  Widget _card(PlanCatalogEntry entry, {required bool pinFooter}) {
    return PlanCard(
      entry: entry,
      busy: busyPlan != null && busyPlan == entry.checkoutPlan,
      showSecondaryCheckout: showSecondaryCheckout,
      compactFeatures: compactFeatures,
      pinFooter: pinFooter,
      onPrimary: () => onSelect(entry),
    );
  }
}

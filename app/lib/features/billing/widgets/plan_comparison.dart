import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../models/billing_plans.dart';
import 'plan_card.dart';

/// Horizontal plan rail inside the cool stage wash.
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
  final double minCardWidth;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final wide = MediaQuery.sizeOf(context).width >= 1100;

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
                style: type.displaySmall,
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
                      Expanded(child: _card(plans[i])),
                    ],
                  ],
                ),
              )
            else
              SizedBox(
                height: compactFeatures ? 420 : 480,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: plans.length,
                  separatorBuilder: (_, _) =>
                      const SizedBox(width: AppSpacing.grid * 2),
                  itemBuilder: (context, i) {
                    return SizedBox(
                      width: minCardWidth,
                      child: _card(plans[i]),
                    );
                  },
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _card(PlanCatalogEntry entry) {
    return PlanCard(
      entry: entry,
      busy: busyPlan != null && busyPlan == entry.checkoutPlan,
      showSecondaryCheckout: showSecondaryCheckout,
      compactFeatures: compactFeatures,
      onPrimary: () => onSelect(entry),
    );
  }
}

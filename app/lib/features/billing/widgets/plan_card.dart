import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../models/billing_plans.dart';

/// Single plan comparison card (interactive container — Care.com / Apple style).
class PlanCard extends StatelessWidget {
  const PlanCard({
    super.key,
    required this.entry,
    required this.onPrimary,
    this.busy = false,
    this.showSecondaryCheckout = false,
    this.compactFeatures = false,
  });

  final PlanCatalogEntry entry;
  final VoidCallback? onPrimary;
  final bool busy;
  final bool showSecondaryCheckout;
  final bool compactFeatures;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final scheme = Theme.of(context).colorScheme;
    final isPaid = entry.checkoutPlan != null;

    final badgeBg = entry.limited
        ? scheme.surfaceContainerHighest
        : entry.recommended || entry.kind == PlanCardKind.plus
        ? colors.accentSoft
        : colors.oneTimeBadgeBg;
    final badgeFg = entry.limited
        ? colors.muted
        : entry.recommended || entry.kind == PlanCardKind.plus
        ? scheme.primary
        : colors.link;

    return AnimatedContainer(
      duration: const Duration(milliseconds: 160),
      curve: Curves.easeOut,
      decoration: BoxDecoration(
        color: entry.limited
            ? Color.lerp(colors.stage, Colors.white, 0.45)
            : scheme.surface,
        borderRadius: BorderRadius.circular(AppSpacing.cardRadius),
        border: Border.all(
          color: entry.recommended ? scheme.primary : Colors.transparent,
          width: entry.recommended ? 1.5 : 1.5,
        ),
        boxShadow: entry.recommended
            ? [
                BoxShadow(
                  color: scheme.primary.withValues(alpha: 0.12),
                  blurRadius: 0,
                  spreadRadius: 1,
                ),
              ]
            : null,
      ),
      padding: const EdgeInsets.all(AppSpacing.grid * 3),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Align(
            alignment: Alignment.centerLeft,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: badgeBg,
                borderRadius: BorderRadius.circular(AppSpacing.pillRadius),
              ),
              child: Text(
                entry.badge.toUpperCase(),
                style: type.labelSmall?.copyWith(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.04 * 11,
                  color: badgeFg,
                ),
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.grid * 1.5),
          Text(entry.name, style: type.headlineSmall),
          const SizedBox(height: AppSpacing.grid),
          SizedBox(
            height: compactFeatures ? 40 : 44,
            child: Text(
              entry.benefit,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: type.bodyMedium?.copyWith(
                color: colors.muted,
                height: 1.4,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.grid * 2),
          Text(
            entry.price,
            style: type.titleMedium?.copyWith(
              fontSize: 20,
              fontWeight: FontWeight.w700,
              letterSpacing: -0.02 * 20,
            ),
          ),
          const SizedBox(height: AppSpacing.grid * 0.5),
          Text(
            entry.meta,
            style: type.bodySmall?.copyWith(
              color: colors.muted,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: AppSpacing.grid * 2.5),
          ...entry.features.map(
            (f) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 16,
                    height: 16,
                    margin: const EdgeInsets.only(top: 1),
                    decoration: BoxDecoration(
                      color: colors.accentSoft,
                      shape: BoxShape.circle,
                    ),
                    child: Icon(Icons.check, size: 12, color: scheme.primary),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      f,
                      style: type.bodySmall?.copyWith(
                        color: colors.label,
                        height: 1.35,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const Spacer(),
          const SizedBox(height: AppSpacing.grid),
          if (isPaid)
            FilledButton(
              onPressed: busy ? null : onPrimary,
              child: busy
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : Text(entry.ctaLabel),
            )
          else
            OutlinedButton(
              onPressed: busy ? null : onPrimary,
              style: OutlinedButton.styleFrom(
                foregroundColor: scheme.primary,
                side: BorderSide(color: scheme.primary, width: 1.5),
                minimumSize: const Size.fromHeight(AppSpacing.controlHeight),
                shape: const StadiumBorder(),
              ),
              child: Text(entry.ctaLabel),
            ),
          if (showSecondaryCheckout && isPaid) ...[
            const SizedBox(height: AppSpacing.grid * 1.25),
            TextButton(
              onPressed: busy ? null : onPrimary,
              child: const Text('Checkout →'),
            ),
          ],
        ],
      ),
    );
  }
}

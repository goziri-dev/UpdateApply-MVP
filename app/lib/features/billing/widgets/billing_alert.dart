import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';

enum BillingAlertTone { error, success }

/// Inline success / error banner for Credits hub and paywall.
class BillingAlert extends StatelessWidget {
  const BillingAlert({
    super.key,
    required this.tone,
    required this.message,
    this.actionLabel,
    this.onAction,
    this.onDismiss,
  });

  final BillingAlertTone tone;
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;
  final VoidCallback? onDismiss;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final scheme = Theme.of(context).colorScheme;
    final bg = tone == BillingAlertTone.error
        ? colors.dangerBg
        : colors.successBg;
    final fg = tone == BillingAlertTone.error ? scheme.error : scheme.primary;

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.grid * 2,
        vertical: AppSpacing.grid * 1.75,
      ),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(AppSpacing.markRadius),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Text(
              message,
              style: type.bodyMedium?.copyWith(
                color: fg,
                fontWeight: FontWeight.w500,
                height: 1.4,
              ),
            ),
          ),
          if (actionLabel != null && onAction != null)
            TextButton(onPressed: onAction, child: Text(actionLabel!)),
          if (onDismiss != null)
            TextButton(onPressed: onDismiss, child: const Text('Dismiss')),
        ],
      ),
    );
  }
}

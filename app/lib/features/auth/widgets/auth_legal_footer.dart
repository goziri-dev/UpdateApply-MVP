import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';

class AuthLegalFooter extends StatelessWidget {
  const AuthLegalFooter({super.key});

  void _showPlaceholder(BuildContext context, String title) {
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: Text(
          '$title will live here once the legal copy is ready.',
          style: Theme.of(context).textTheme.bodyMedium,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final colors = context.appColors;
    final type = Theme.of(context).textTheme;

    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.grid * 4.5),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          TextButton(
            onPressed: () => _showPlaceholder(context, 'Terms'),
            style: TextButton.styleFrom(
              foregroundColor: colors.legal,
              textStyle: type.labelSmall,
              minimumSize: Size.zero,
              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
            ),
            child: const Text('Terms'),
          ),
          const SizedBox(width: AppSpacing.grid * 2.5),
          TextButton(
            onPressed: () => _showPlaceholder(context, 'Privacy'),
            style: TextButton.styleFrom(
              foregroundColor: colors.legal,
              textStyle: type.labelSmall,
              minimumSize: Size.zero,
              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
            ),
            child: const Text('Privacy'),
          ),
        ],
      ),
    );
  }
}

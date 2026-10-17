import 'package:flutter/material.dart';

import '../../../core/theme/app_theme.dart';

/// Provisional forest `u+` mark from `prototypes/auth/` (not an official logo).
class AuthBrandMark extends StatelessWidget {
  const AuthBrandMark({super.key});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final type = Theme.of(context).textTheme;

    return Center(
      child: Container(
        width: 44,
        height: 44,
        decoration: BoxDecoration(
          color: scheme.primary,
          borderRadius: BorderRadius.circular(AppSpacing.markRadius),
          boxShadow: const [
            BoxShadow(color: Color(0x0A000000), offset: Offset(0, 1)),
          ],
        ),
        child: Stack(
          children: [
            Center(
              child: Text(
                'u',
                style: type.headlineMedium?.copyWith(
                  color: scheme.onPrimary,
                  fontSize: 22,
                  height: 1,
                  letterSpacing: -0.04 * 22,
                ),
              ),
            ),
            Positioned(
              top: 6,
              right: 7,
              child: Text(
                '+',
                style: type.labelSmall?.copyWith(
                  color: scheme.onPrimary,
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  height: 1,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

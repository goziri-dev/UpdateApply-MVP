import 'package:flutter/material.dart';
import 'package:signals/signals_flutter.dart';

import '../../../core/theme/app_theme.dart';
import '../state/auth_state.dart';

/// Inline alert for auth errors or success notices.
class AuthFeedbackBanner extends StatelessWidget {
  const AuthFeedbackBanner({super.key});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final type = Theme.of(context).textTheme;

    return SignalBuilder(
      builder: (context) {
        final error = authError.value;
        final notice = authNotice.value;
        final message = error ?? notice;
        if (message == null || message.isEmpty) {
          return const SizedBox.shrink();
        }

        final isError = error != null;
        return Padding(
          padding: const EdgeInsets.only(bottom: AppSpacing.grid * 2),
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: isError
                  ? scheme.errorContainer
                  : scheme.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.grid * 2,
                vertical: AppSpacing.grid * 1.5,
              ),
              child: Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  message,
                  style: type.bodyMedium?.copyWith(
                    color: isError ? scheme.error : scheme.onSurface,
                    height: 1.4,
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

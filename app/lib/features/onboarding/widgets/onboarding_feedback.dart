import 'package:flutter/material.dart';
import 'package:signals_flutter/signals_flutter.dart';

import '../../../core/theme/app_theme.dart';
import '../state/onboarding_state.dart';

class OnboardingFeedbackBanner extends StatelessWidget {
  const OnboardingFeedbackBanner({super.key});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final type = Theme.of(context).textTheme;

    return SignalBuilder(
      builder: (context) {
        final error = onboardingError.value;
        final info = onboardingInfo.value;
        final message = error ?? info;
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

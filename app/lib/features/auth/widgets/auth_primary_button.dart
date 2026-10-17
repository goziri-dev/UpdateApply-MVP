import 'package:flutter/material.dart';
import 'package:signals/signals_flutter.dart';

import '../../../core/theme/app_theme.dart';
import '../state/auth_state.dart';

class AuthPrimaryButton extends StatelessWidget {
  const AuthPrimaryButton({
    super.key,
    required this.idleLabel,
    required this.loadingLabel,
    required this.onPressed,
    this.busyTarget = AuthBusyTarget.email,
  });

  final String idleLabel;
  final String loadingLabel;
  final VoidCallback? onPressed;
  final AuthBusyTarget busyTarget;

  @override
  Widget build(BuildContext context) {
    return SignalBuilder(
      builder: (context) {
        final busy = authBusy.value;
        final isLoading = busy == busyTarget;
        final disabled = busy != AuthBusyTarget.idle;

        return Padding(
          padding: const EdgeInsets.only(top: AppSpacing.grid),
          child: FilledButton(
            onPressed: disabled ? null : onPressed,
            child: isLoading
                ? Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Theme.of(context).colorScheme.onPrimary,
                        ),
                      ),
                      const SizedBox(width: AppSpacing.grid * 1.25),
                      Text(loadingLabel),
                    ],
                  )
                : Text(idleLabel),
          ),
        );
      },
    );
  }
}

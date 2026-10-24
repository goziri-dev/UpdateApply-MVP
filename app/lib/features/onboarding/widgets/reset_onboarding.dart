import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../state/onboarding_state.dart';

/// Destructive confirm → ``POST /onboarding/reset`` → hard-gate upload.
///
/// Returns true when reset succeeded and navigation was requested.
Future<bool> confirmAndResetOnboarding(BuildContext context) async {
  final confirmed = await showDialog<bool>(
    context: context,
    builder: (dialogContext) {
      final type = Theme.of(dialogContext).textTheme;
      final scheme = Theme.of(dialogContext).colorScheme;
      final colors = dialogContext.appColors;

      return AlertDialog(
        title: Text(
          'Start over?',
          style: type.titleMedium?.copyWith(fontWeight: FontWeight.w700),
        ),
        content: Text(
          'This clears your remade master profile and asks you to upload a '
          'new resume. Tailored application history stays. This cannot be '
          'undone.',
          style: type.bodyMedium?.copyWith(color: colors.muted, height: 1.45),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            style: TextButton.styleFrom(foregroundColor: scheme.error),
            child: const Text('Reset profile'),
          ),
        ],
      );
    },
  );
  if (confirmed != true || !context.mounted) return false;

  clearOnboardingFeedback();
  onboardingBusy.value = true;
  try {
    await onboardingService.reset();
    await refreshOnboardingGate(statusHint: 'not_started');
    if (!context.mounted) return true;
    context.go('/onboarding/upload');
    return true;
  } on DioException catch (e) {
    final detail = e.response?.data;
    final message = detail is Map && detail['detail'] != null
        ? detail['detail'].toString()
        : (e.message ?? 'Could not reset profile');
    if (context.mounted) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(message)));
    }
    return false;
  } on Object catch (e) {
    if (context.mounted) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.toString())));
    }
    return false;
  } finally {
    onboardingBusy.value = false;
  }
}

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:signals/signals_flutter.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../../../services/api_client.dart';
import '../../auth/state/auth_state.dart';
import '../../resume/widgets/resume_preview.dart';
import '../state/home_state.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  Future<void> _verifySession(BuildContext context) async {
    try {
      final me = await apiClient.authMe();
      if (!context.mounted) return;
      final email = me['email'] as String? ?? me['id'] as String? ?? 'ok';
      setHomeMessage('Backend verified session for $email');
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('Session verified: $email')));
    } on DioException catch (error) {
      if (!context.mounted) return;
      final detail = error.response?.data;
      final message = detail is Map && detail['detail'] != null
          ? detail['detail'].toString()
          : (error.message ?? 'Request failed');
      setHomeMessage('Session verify failed: $message');
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('Verify failed: $message')));
    } on Object catch (error) {
      if (!context.mounted) return;
      setHomeMessage('Session verify failed: $error');
    }
  }

  Future<void> _signOut() async {
    await signOut();
  }

  @override
  Widget build(BuildContext context) {
    final user = authRepository.service.currentUser;
    final email = user?.email ?? user?.id ?? 'signed in';
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;

    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(AppSpacing.grid * 3),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('UpdateApply', style: type.headlineMedium),
              const SizedBox(height: AppSpacing.grid * 1.5),
              Text(
                'Signed in as $email',
                style: type.bodyMedium?.copyWith(color: colors.muted),
              ),
              const SizedBox(height: AppSpacing.grid * 1.5),
              SignalBuilder(
                builder: (context) {
                  return Text(homeMessage.value, style: type.bodyLarge);
                },
              ),
              const SizedBox(height: AppSpacing.grid * 3),
              Text('Your resume', style: type.titleMedium),
              const SizedBox(height: AppSpacing.grid),
              Text(
                'Tap the preview to enlarge or download.',
                style: type.bodySmall?.copyWith(color: colors.muted),
              ),
              const SizedBox(height: AppSpacing.grid * 2),
              ResumePreview(
                mode: ResumePreviewMode.mini,
                viewTypePrefix: 'resume-home-mini',
                onTap: () => showResumePreviewModal(context),
              ),
              const SizedBox(height: AppSpacing.grid * 3),
              Text(
                'Paste a job description to generate a tailored resume from '
                'your remade master profile.',
                style: type.bodyMedium?.copyWith(
                  color: colors.muted,
                  height: 1.45,
                  fontWeight: FontWeight.w400,
                ),
              ),
              const SizedBox(height: AppSpacing.grid * 2),
              FilledButton(
                onPressed: () => context.go('/tailor'),
                child: const Text('Tailor to a job description'),
              ),
              const SizedBox(height: AppSpacing.grid),
              OutlinedButton(
                onPressed: () => _verifySession(context),
                child: const Text('Verify session with API'),
              ),
              const SizedBox(height: AppSpacing.grid),
              TextButton(onPressed: _signOut, child: const Text('Sign out')),
            ],
          ),
        ),
      ),
    );
  }
}

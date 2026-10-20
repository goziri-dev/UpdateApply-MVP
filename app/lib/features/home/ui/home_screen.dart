import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:signals/signals_flutter.dart';

import '../../../services/api_client.dart';
import '../../auth/state/auth_state.dart';
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

    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'UpdateApply',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 12),
              Text(
                'Signed in as $email',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 12),
              SignalBuilder(
                builder: (context) {
                  return Text(
                    homeMessage.value,
                    style: Theme.of(context).textTheme.bodyLarge,
                  );
                },
              ),
              const SizedBox(height: 24),
              Text(
                'MVP: tailor-first. Profile + tailor screens come next.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: () => _verifySession(context),
                child: const Text('Verify session with API'),
              ),
              const SizedBox(height: 8),
              TextButton(onPressed: _signOut, child: const Text('Sign out')),
            ],
          ),
        ),
      ),
    );
  }
}

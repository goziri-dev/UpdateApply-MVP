import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_web_plugins/url_strategy.dart';
import 'package:go_router/go_router.dart';
import 'package:scoped_deps/scoped_deps.dart';

import 'core/routing/app_router.dart';
import 'core/routing/auth_router_refresh.dart';
import 'core/theme/app_theme.dart';
import 'features/applications/state/applications_state.dart';
import 'features/auth/services/supabase_bootstrap.dart';
import 'features/auth/state/auth_state.dart';
import 'features/jobs_for_you/state/jobs_for_you_state.dart';
import 'features/onboarding/state/onboarding_state.dart';
import 'features/resume/state/master_resume_state.dart';
import 'services/api_client.dart';

Future<void> main() async {
  // Path URLs (`/auth`) instead of hash (`/#/auth`) — must run before binding.
  usePathUrlStrategy();

  // Binding + runApp must share the same zone (Flutter zone-mismatch rules).
  // ensureInitialized outside runScoped made GoRouter redirects resolve
  // onboardingGate via orElse fallbacks while auth sync wrote the scoped
  // signal — leaving /boot on "Checking your profile…" forever.
  await runScoped(
    () async {
      WidgetsFlutterBinding.ensureInitialized();

      try {
        try {
          await bootstrapSupabase();
        } finally {
          // Always release the auth gate — even if Supabase init fails we still
          // show the error app / auth UI rather than hang on /boot.
          markAuthHydrated();
        }
        final refresh = AuthRouterRefresh();
        final router = createAppRouter(refresh);
        runApp(UpdateApplyApp(routerConfig: router, authRefresh: refresh));
      } on Object catch (error, stackTrace) {
        debugPrint('UpdateApply bootstrap failed: $error\n$stackTrace');
        markAuthHydrated();
        runApp(_BootstrapErrorApp(error: error, stackTrace: stackTrace));
      }
    },
    values: {
      authRepositoryRef,
      authBusyRef,
      authErrorRef,
      authNoticeRef,
      authHydratedRef,
      apiClientRef,
      onboardingServiceRef,
      onboardingGateRef,
      onboardingGateSyncingRef,
      onboardingGateSyncErrorRef,
      onboardingBusyRef,
      onboardingErrorRef,
      onboardingInfoRef,
      applicationsEpochRef,
      jobsForYouEpochRef,
      jobsForYouCacheRef,
      masterResumeEpochRef,
    },
  );
}

/// Surfaced when Supabase/router bootstrap throws before the first frame.
class _BootstrapErrorApp extends StatelessWidget {
  const _BootstrapErrorApp({required this.error, this.stackTrace});

  final Object error;
  final StackTrace? stackTrace;

  @override
  Widget build(BuildContext context) {
    final detail = kDebugMode && stackTrace != null
        ? '$error\n\n$stackTrace'
        : '$error';
    return MaterialApp(
      title: 'UpdateApply',
      theme: AppTheme.light(),
      home: Scaffold(
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: SelectableText(
              'UpdateApply failed to start.\n\n$detail',
              style: const TextStyle(fontSize: 14, height: 1.4),
            ),
          ),
        ),
      ),
    );
  }
}

class UpdateApplyApp extends StatefulWidget {
  const UpdateApplyApp({
    super.key,
    required this.routerConfig,
    required this.authRefresh,
  });

  final GoRouter routerConfig;
  final AuthRouterRefresh authRefresh;

  @override
  State<UpdateApplyApp> createState() => _UpdateApplyAppState();
}

class _UpdateApplyAppState extends State<UpdateApplyApp> {
  @override
  void dispose() {
    widget.authRefresh.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'UpdateApply',
      theme: AppTheme.light(),
      routerConfig: widget.routerConfig,
    );
  }
}

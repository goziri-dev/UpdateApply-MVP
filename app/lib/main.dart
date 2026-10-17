import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:scoped_deps/scoped_deps.dart';

import 'core/routing/app_router.dart';
import 'core/routing/auth_router_refresh.dart';
import 'core/theme/app_theme.dart';
import 'features/auth/services/supabase_bootstrap.dart';
import 'features/auth/state/auth_state.dart';
import 'features/home/state/home_state.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await bootstrapSupabase();
  runScoped(
    () {
      final refresh = AuthRouterRefresh();
      final router = createAppRouter(refresh);
      runApp(UpdateApplyApp(routerConfig: router, authRefresh: refresh));
    },
    values: {
      homeMessageRef,
      authRepositoryRef,
      authBusyRef,
      authErrorRef,
      authNoticeRef,
    },
  );
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

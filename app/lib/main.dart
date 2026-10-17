import 'package:flutter/material.dart';
import 'package:scoped_deps/scoped_deps.dart';

import 'core/routing/app_router.dart';
import 'core/theme/app_theme.dart';
import 'features/home/state/home_state.dart';

void main() {
  runScoped(() => runApp(const UpdateApplyApp()), values: {homeMessageRef});
}

class UpdateApplyApp extends StatelessWidget {
  const UpdateApplyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'UpdateApply',
      theme: AppTheme.light(),
      routerConfig: appRouter,
    );
  }
}

import 'package:go_router/go_router.dart';

import '../../features/auth/ui/auth_placeholder_screen.dart';
import '../../features/home/ui/home_screen.dart';

final GoRouter appRouter = GoRouter(
  initialLocation: '/',
  routes: [
    GoRoute(path: '/', builder: (context, state) => const HomeScreen()),
    GoRoute(
      path: '/auth',
      builder: (context, state) => const AuthPlaceholderScreen(),
    ),
  ],
);

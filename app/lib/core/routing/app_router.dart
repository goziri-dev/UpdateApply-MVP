import 'package:go_router/go_router.dart';

import '../../features/auth/state/auth_state.dart';
import '../../features/auth/ui/auth_screen.dart';
import '../../features/home/ui/home_screen.dart';
import 'auth_router_refresh.dart';

GoRouter createAppRouter(AuthRouterRefresh refresh) {
  return GoRouter(
    initialLocation: '/',
    refreshListenable: refresh,
    redirect: (context, state) {
      final signedIn = authRepository.isSignedIn;
      final onAuth = state.matchedLocation == '/auth';

      if (!signedIn && !onAuth) return '/auth';
      if (signedIn && onAuth) return '/';
      return null;
    },
    routes: [
      GoRoute(path: '/', builder: (context, state) => const HomeScreen()),
      GoRoute(path: '/auth', builder: (context, state) => const AuthScreen()),
    ],
  );
}

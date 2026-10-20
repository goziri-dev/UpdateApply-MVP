import 'package:go_router/go_router.dart';

import '../../features/auth/state/auth_state.dart';
import '../../features/auth/ui/auth_screen.dart';
import '../../features/home/ui/home_screen.dart';
import '../../features/onboarding/state/onboarding_state.dart';
import '../../features/onboarding/ui/interview_screen.dart';
import '../../features/onboarding/ui/parsing_screen.dart';
import '../../features/onboarding/ui/ready_screen.dart';
import '../../features/onboarding/ui/review_screen.dart';
import '../../features/onboarding/ui/upload_screen.dart';
import 'auth_router_refresh.dart';

bool _isOnboardingPath(String location) => location.startsWith('/onboarding');

GoRouter createAppRouter(AuthRouterRefresh refresh) {
  return GoRouter(
    initialLocation: '/',
    refreshListenable: refresh,
    redirect: (context, state) {
      final signedIn = authRepository.isSignedIn;
      final location = state.matchedLocation;
      final onAuth = location == '/auth';
      final onOnboarding = _isOnboardingPath(location);
      final gate = onboardingGate.value;

      if (!signedIn) {
        return onAuth ? null : '/auth';
      }

      // Signed in: leave auth. Prefer onboarding until complete.
      if (onAuth) {
        if (gate == OnboardingGate.complete) return '/';
        return '/onboarding/upload';
      }

      // Treat unknown like incomplete so the hard gate never leaks into home.
      if (gate != OnboardingGate.complete && !onOnboarding) {
        return '/onboarding/upload';
      }

      if (gate == OnboardingGate.complete && onOnboarding) {
        // Allow ready screen only until they hit complete → home.
        if (location == '/onboarding/ready') return null;
        return '/';
      }

      return null;
    },
    routes: [
      GoRoute(path: '/', builder: (context, state) => const HomeScreen()),
      GoRoute(path: '/auth', builder: (context, state) => const AuthScreen()),
      GoRoute(
        path: '/onboarding/upload',
        builder: (context, state) => const OnboardingUploadScreen(),
      ),
      GoRoute(
        path: '/onboarding/parsing',
        builder: (context, state) => const OnboardingParsingScreen(),
      ),
      GoRoute(
        path: '/onboarding/interview',
        builder: (context, state) => const OnboardingInterviewScreen(),
      ),
      GoRoute(
        path: '/onboarding/review',
        builder: (context, state) => const OnboardingReviewScreen(),
      ),
      GoRoute(
        path: '/onboarding/ready',
        builder: (context, state) => const OnboardingReadyScreen(),
      ),
    ],
  );
}

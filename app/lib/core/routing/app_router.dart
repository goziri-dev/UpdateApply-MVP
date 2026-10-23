import 'package:go_router/go_router.dart';

import '../../features/auth/state/auth_state.dart';
import '../../features/auth/ui/auth_screen.dart';
import '../../features/home/ui/home_screen.dart';
import '../../features/onboarding/state/onboarding_state.dart';
import '../../features/onboarding/ui/gate_loading_screen.dart';
import '../../features/onboarding/ui/interview_screen.dart';
import '../../features/onboarding/ui/parsing_screen.dart';
import '../../features/onboarding/ui/review_screen.dart';
import '../../features/onboarding/ui/upload_screen.dart';
import '../../features/resume/ui/resume_reveal_screen.dart';
import '../../features/tailor/ui/tailor_screen.dart';
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
      final onBoot = location == '/boot';
      final onOnboarding = _isOnboardingPath(location);
      final gate = onboardingGate.value;

      if (!signedIn) {
        return onAuth ? null : '/auth';
      }

      // Status not loaded yet (or API unreachable) — never invent "needs
      // onboarding." Hold on /boot until we know.
      if (gate == OnboardingGate.unknown) {
        return onBoot ? null : '/boot';
      }

      if (onBoot) {
        // Gate resolved — leave the loading screen.
        if (gate == OnboardingGate.complete) return '/';
        return '/onboarding/upload';
      }

      // Signed in: leave auth. Prefer onboarding until complete.
      if (onAuth) {
        if (gate == OnboardingGate.complete) return '/';
        return '/onboarding/upload';
      }

      if (gate != OnboardingGate.complete && !onOnboarding) {
        return '/onboarding/upload';
      }

      if (gate == OnboardingGate.complete && onOnboarding) {
        // Allow reveal/ready until they leave for the dashboard.
        if (location == '/onboarding/reveal' ||
            location == '/onboarding/ready') {
          return null;
        }
        return '/';
      }

      return null;
    },
    routes: [
      GoRoute(path: '/', builder: (context, state) => const HomeScreen()),
      GoRoute(
        path: '/tailor',
        builder: (context, state) => const TailorScreen(),
      ),
      GoRoute(path: '/auth', builder: (context, state) => const AuthScreen()),
      GoRoute(
        path: '/boot',
        builder: (context, state) => GateLoadingScreen(authRefresh: refresh),
      ),
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
        path: '/onboarding/reveal',
        builder: (context, state) => const ResumeRevealScreen(),
      ),
      GoRoute(
        path: '/onboarding/ready',
        // Legacy path — same unlock moment as reveal.
        builder: (context, state) => const ResumeRevealScreen(),
      ),
    ],
  );
}

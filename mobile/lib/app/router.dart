import 'package:go_router/go_router.dart';

import '../features/auth/presentation/login_screen.dart';
import '../features/auth/presentation/register_screen.dart';
import '../features/home/presentation/home_screen.dart';
import '../features/invitations/presentation/guest_name_screen.dart';
import '../features/invitations/presentation/invitation_details_screen.dart';
import '../features/journeys/presentation/create_journey_screen.dart';
import '../features/journeys/presentation/host_live_journey_screen.dart';
import '../features/journeys/presentation/journey_created_screen.dart';
import '../features/privacy/presentation/privacy_dashboard_screen.dart';
import '../features/profile/presentation/profile_screen.dart';

/// Typed navigation with deep-link support for /join/<token> (spec §43).
final router = GoRouter(
  initialLocation: '/home',
  routes: [
    GoRoute(path: '/home', builder: (_, __) => const HomeScreen()),
    GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
    GoRoute(path: '/register', builder: (_, __) => const RegisterScreen()),
    GoRoute(
      path: '/journeys/new',
      builder: (_, __) => const CreateJourneyScreen(),
    ),
    GoRoute(
      path: '/journeys/:id/invited',
      builder: (_, s) => JourneyCreatedScreen(
        journeyId: s.pathParameters['id']!,
      ),
    ),
    GoRoute(
      path: '/journeys/:id/live',
      builder: (_, s) => HostLiveJourneyScreen(
        journeyId: s.pathParameters['id']!,
      ),
    ),
    GoRoute(
      path: '/join/:token',
      builder: (_, s) => InvitationDetailsScreen(
        rawToken: s.pathParameters['token']!,
      ),
    ),
    GoRoute(
      path: '/join/:token/guest',
      builder: (_, s) => GuestNameScreen(rawToken: s.pathParameters['token']!),
    ),
    GoRoute(
      path: '/privacy',
      builder: (_, __) => const PrivacyDashboardScreen(),
    ),
    GoRoute(path: '/profile', builder: (_, __) => const ProfileScreen()),
  ],
);

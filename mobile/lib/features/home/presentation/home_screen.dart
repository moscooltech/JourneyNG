import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/storage/token_storage.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tokens = ref.watch(tokenStorageProvider);
    final isSignedIn = tokens.accessToken != null;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Journey'),
        actions: [
          IconButton(
            icon: const Icon(Icons.privacy_tip_outlined),
            tooltip: 'Privacy',
            onPressed: () => context.go('/privacy'),
          ),
          IconButton(
            icon: const Icon(Icons.person_outline),
            tooltip: 'Profile',
            onPressed: () => context.go(isSignedIn ? '/profile' : '/login'),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          Text(
            'Share your journey, not just your location.',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 8),
          Text(
            'Invite people to come to you and see their trip — only while '
            'they choose to share.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 32),
          FilledButton.icon(
            onPressed: () => context.go('/journeys/new'),
            icon: const Icon(Icons.add_location_alt_outlined),
            label: const Text('Create Journey'),
          ),
          const SizedBox(height: 12),
          if (!isSignedIn)
            OutlinedButton(
              onPressed: () => context.go('/login'),
              child: const Text('Log in / Create account'),
            ),
          const SizedBox(height: 32),
          Text('How it works', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          const ListTile(
            leading: Icon(Icons.link),
            title: Text('1. Create a journey to your destination'),
          ),
          const ListTile(
            leading: Icon(Icons.share),
            title: Text('2. Share the invite link'),
          ),
          const ListTile(
            leading: Icon(Icons.travel_explore),
            title: Text('3. Watch trips arrive live — with consent'),
          ),
        ],
      ),
    );
  }
}

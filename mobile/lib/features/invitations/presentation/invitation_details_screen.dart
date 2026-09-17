import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// Invitation details + consent explanation (spec §18, §23).
/// Clearly states who sees the location, why, for how long, and how to stop.
class InvitationDetailsScreen extends StatelessWidget {
  const InvitationDetailsScreen({super.key, required this.rawToken});

  final String rawToken;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Journey invitation')),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          const Card(
            child: Padding(
              padding: EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'You are invited to share your journey',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
                  ),
                  SizedBox(height: 8),
                  Text(
                    'The person who invited you will see your location on a map '
                    'while you travel to the destination.',
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          const Text('What this means:'),
          const SizedBox(height: 8),
          const ListTile(
            leading: Icon(Icons.visibility),
            title: Text('Who can see your location'),
            subtitle: Text('Only the person who invited you — for this trip.'),
          ),
          const ListTile(
            leading: Icon(Icons.schedule),
            title: Text('When sharing ends'),
            subtitle: Text(
                'When you arrive, when the trip expires, or whenever you tap Stop Sharing.'),
          ),
          const ListTile(
            leading: Icon(Icons.notifications_active),
            title: Text('You stay in control'),
            subtitle: Text(
                'A notification stays visible while sharing. You can stop any time.'),
          ),
          const SizedBox(height: 24),
          FilledButton(
            onPressed: () => context.go('/join/$rawToken/guest'),
            child: const Text('I understand — continue'),
          ),
          const SizedBox(height: 8),
          TextButton(
            onPressed: () => context.go('/home'),
            child: const Text('No thanks'),
          ),
        ],
      ),
    );
  }
}

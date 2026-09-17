import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../journeys/data/journey_repository.dart';

class GuestNameScreen extends ConsumerStatefulWidget {
  const GuestNameScreen({super.key, required this.rawToken});

  final String rawToken;

  @override
  ConsumerState<GuestNameScreen> createState() => _GuestNameScreenState();
}

class _GuestNameScreenState extends ConsumerState<GuestNameScreen> {
  final _name = TextEditingController();
  bool _joining = false;
  String? _error;
  String? _joinedJourneyId;

  Future<void> _join() async {
    setState(() {
      _joining = true;
      _error = null;
    });
    try {
      final journeyId = await ref
          .read(journeyRepositoryProvider)
          .joinAsGuest(widget.rawToken, _name.text.trim());
      setState(() => _joinedJourneyId = journeyId);
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _joining = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Join as guest')),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          if (_joinedJourneyId != null) ...[
            const Text(
              "You've joined the journey. Next: allow location access, "
              'then start sharing.',
              style: TextStyle(fontSize: 16),
            ),
            const SizedBox(height: 24),
            const _GuestReadyFlow(journeyId: null),
          ] else ...[
            TextField(
              controller: _name,
              decoration: const InputDecoration(
                labelText: 'Your name',
                hintText: 'How the host will see you',
              ),
            ),
            const SizedBox(height: 24),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: Text(_error!,
                    style:
                        TextStyle(color: Theme.of(context).colorScheme.error)),
              ),
            FilledButton(
              onPressed: _joining ? null : _join,
              child: _joining
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(strokeWidth: 2))
                  : const Text('Join journey'),
            ),
          ],
        ],
      ),
    );
  }
}

class _GuestReadyFlow extends StatelessWidget {
  const _GuestReadyFlow({this.journeyId});

  final String? journeyId;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        const ListTile(
          leading: Icon(Icons.lock_outline),
          title: Text('Allow location access'),
          subtitle: Text('Required to share your journey. You approve this.'),
        ),
        const ListTile(
          leading: Icon(Icons.play_circle_outline),
          title: Text('Start sharing'),
          subtitle: Text('A notification will stay visible while sharing.'),
        ),
      ],
    );
  }
}

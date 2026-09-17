import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../data/journey_repository.dart';

class JourneyCreatedScreen extends ConsumerStatefulWidget {
  const JourneyCreatedScreen({super.key, required this.journeyId});

  final String journeyId;

  @override
  ConsumerState<JourneyCreatedScreen> createState() =>
      _JourneyCreatedScreenState();
}

class _JourneyCreatedScreenState extends ConsumerState<JourneyCreatedScreen> {
  String? _inviteUrl;
  bool _starting = false;
  String? _error;

  Future<void> _makeInvite() async {
    try {
      final url = await ref
          .read(journeyRepositoryProvider)
          .createInvitation(widget.journeyId);
      setState(() => _inviteUrl = url);
    } catch (e) {
      setState(() => _error = e.toString());
    }
  }

  Future<void> _start() async {
    setState(() {
      _starting = true;
      _error = null;
    });
    try {
      await ref.read(journeyRepositoryProvider).startJourney(widget.journeyId);
      if (mounted) context.go('/journeys/${widget.journeyId}/live');
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _starting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Invite people')),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          Text(
            'Share this link with the people coming to you. '
            'They choose whether to share their location.',
            style: Theme.of(context).textTheme.bodyLarge,
          ),
          const SizedBox(height: 24),
          if (_inviteUrl != null) ...[
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: SelectableText(_inviteUrl!),
              ),
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: () {
                Clipboard.setData(ClipboardData(text: _inviteUrl!));
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Link copied')),
                );
              },
              icon: const Icon(Icons.copy),
              label: const Text('Copy link'),
            ),
          ] else
            FilledButton.tonal(
              onPressed: _makeInvite,
              child: const Text('Create invitation link'),
            ),
          const SizedBox(height: 32),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: Text(_error!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error)),
            ),
          FilledButton(
            onPressed: _starting ? null : _start,
            child: _starting
                ? const SizedBox(
                    height: 20,
                    width: 20,
                    child: CircularProgressIndicator(strokeWidth: 2))
                : const Text('Start Journey'),
          ),
        ],
      ),
    );
  }
}

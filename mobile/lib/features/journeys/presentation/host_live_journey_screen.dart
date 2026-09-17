import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../data/journey_repository.dart';

/// Host live view: participant cards with status, ETA, last-updated.
/// Live marker updates arrive via WebSocket on the backend; V1 UI polls
/// the authorized /locations endpoint and is the point where Mapbox
/// markers are rendered.
class HostLiveJourneyScreen extends ConsumerStatefulWidget {
  const HostLiveJourneyScreen({super.key, required this.journeyId});

  final String journeyId;

  @override
  ConsumerState<HostLiveJourneyScreen> createState() =>
      _HostLiveJourneyScreenState();
}

class _HostLiveJourneyScreenState extends ConsumerState<HostLiveJourneyScreen> {
  Timer? _poll;
  Map<String, dynamic>? _journey;
  List<Map<String, dynamic>> _locations = [];
  bool _ending = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _refresh();
    _poll = Timer.periodic(const Duration(seconds: 5), (_) => _refresh());
  }

  @override
  void dispose() {
    _poll?.cancel();
    super.dispose();
  }

  Future<void> _refresh() async {
    final repo = ref.read(journeyRepositoryProvider);
    try {
      final journey = await repo.getJourney(widget.journeyId);
      final locations = await repo.getLocations(widget.journeyId);
      if (mounted) {
        setState(() {
          _journey = journey;
          _locations = locations;
          _error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  Future<void> _endJourney() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('End journey?'),
        content: const Text(
          'This will stop location sharing for everyone currently '
          'sharing their location.',
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Keep sharing')),
          FilledButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('End journey')),
        ],
      ),
    );
    if (confirmed != true) return;
    setState(() => _ending = true);
    try {
      await ref.read(journeyRepositoryProvider).endJourney(widget.journeyId);
      if (mounted) context.go('/home');
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _ending = false);
    }
  }

  String _timeAgo(String iso) {
    final t = DateTime.tryParse(iso);
    if (t == null) return 'unknown';
    final diff = DateTime.now().difference(t);
    if (diff.inSeconds < 15) return 'just now';
    if (diff.inSeconds < 60) return '${diff.inSeconds}s ago';
    return '${diff.inMinutes}m ago';
  }

  @override
  Widget build(BuildContext context) {
    final participants =
        (_journey?['participants'] as List?)?.cast<Map<String, dynamic>>() ?? [];

    return Scaffold(
      appBar: AppBar(
        title: const Text('Live journey'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _refresh),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (_error != null)
            Card(
              color: Theme.of(context).colorScheme.errorContainer,
              child: const Padding(
                padding: EdgeInsets.all(12),
                child: Text('Connection problem. Retrying…'),
              ),
            ),
          if (_journey != null)
            Card(
              child: ListTile(
                leading: const Icon(Icons.flag),
                title: Text(_journey!['journey']['destination_name'] ?? 'Destination'),
                subtitle: Text('Status: ${_journey!['journey']['status']}'),
              ),
            ),
          const SizedBox(height: 16),
          if (participants.isEmpty)
            const Center(child: Text('Waiting for people to join…'))
          else
            ...participants.map((p) => _ParticipantCard(
                  name: p['display_name']?.toString() ?? 'Visitor',
                  status: p['status']?.toString() ?? 'PENDING',
                  lastUpdated: _lastUpdatedFor(p),
                )),
          const SizedBox(height: 24),
          FilledButton(
            onPressed: _ending ? null : _endJourney,
            child: _ending
                ? const SizedBox(
                    height: 20,
                    width: 20,
                    child: CircularProgressIndicator(strokeWidth: 2))
                : const Text('End Journey'),
          ),
        ],
      ),
    );
  }

  String? _lastUpdatedFor(Map<String, dynamic> p) {
    final id = p['id'];
    for (final loc in _locations) {
      if (loc['participant_id'] == id) {
        return _timeAgo(loc['received_at'] as String);
      }
    }
    return null;
  }
}

class _ParticipantCard extends StatelessWidget {
  const _ParticipantCard({
    required this.name,
    required this.status,
    this.lastUpdated,
  });

  final String name;
  final String status;
  final String? lastUpdated;

  @override
  Widget build(BuildContext context) {
    final statusLabel = {
      'ACTIVE': 'Sharing location',
      'ARRIVED': 'Arrived — sharing ended',
      'INVITED': 'Pending',
      'ACCEPTED': 'Accepted',
      'DECLINED': 'Declined',
      'LEFT': 'Left',
      'REMOVED': 'Removed',
      'EXPIRED': 'Expired',
    }[status] ?? status.toLowerCase();

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Icon(
          status == 'ACTIVE'
              ? Icons.my_location
              : status == 'ARRIVED'
                  ? Icons.check_circle
                  : Icons.person_outline,
        ),
        title: Text(name),
        subtitle: Text([
          statusLabel,
          if (lastUpdated != null) 'Updated $lastUpdated',
        ].join(' · ')),
      ),
    );
  }
}

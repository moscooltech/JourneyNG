import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';

class PrivacyDashboardScreen extends ConsumerStatefulWidget {
  const PrivacyDashboardScreen({super.key});

  @override
  ConsumerState<PrivacyDashboardScreen> createState() =>
      _PrivacyDashboardScreenState();
}

class _PrivacyDashboardScreenState extends ConsumerState<PrivacyDashboardScreen> {
  List<dynamic> _sharing = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final resp = await ref.read(apiClientProvider).get('/privacy/active-sharing');
      setState(() {
        _sharing = resp.data as List<dynamic>;
        _loading = false;
        _error = null;
      });
    } catch (e) {
      setState(() {
        _loading = false;
        _error = 'Could not load sharing status. Are you signed in?';
      });
    }
  }

  Future<void> _stopAll() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Stop all sharing?'),
        content: const Text(
            'Everyone who can currently see your location will lose access immediately.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Stop all')),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await ref.read(apiClientProvider).post('/privacy/stop-all-sharing');
      await _load();
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Privacy')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(24),
              children: [
                Text('Active location sharing',
                    style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 12),
                if (_error != null) Text(_error!),
                if (_sharing.isEmpty && _error == null)
                  const Card(
                    child: ListTile(
                      leading: Icon(Icons.check_circle_outline),
                      title: Text('Nothing is being shared right now'),
                    ),
                  )
                else
                  ..._sharing.map((s) {
                    final item = s as Map;
                    return Card(
                      child: ListTile(
                        leading: const Icon(Icons.share_location),
                        title: Text(item['destination']?.toString() ?? 'Journey'),
                        subtitle: Text(
                          'Purpose: journey to destination\n'
                          'Ends: ${item['expires_at']?.toString() ?? 'on arrival'}',
                        ),
                      ),
                    );
                  }),
                const SizedBox(height: 24),
                if (_sharing.isNotEmpty)
                  FilledButton.tonal(
                    onPressed: _stopAll,
                    child: const Text('Stop All Sharing'),
                  ),
              ],
            ),
    );
  }
}

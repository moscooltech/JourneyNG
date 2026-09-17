import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../data/journey_repository.dart';

class CreateJourneyScreen extends ConsumerStatefulWidget {
  const CreateJourneyScreen({super.key});

  @override
  ConsumerState<CreateJourneyScreen> createState() => _CreateJourneyScreenState();
}

class _CreateJourneyScreenState extends ConsumerState<CreateJourneyScreen> {
  final _name = TextEditingController();
  double _lat = 6.5244;
  double _lng = 3.3792;
  int _durationMinutes = 120;
  bool _creating = false;
  String? _error;

  Future<void> _create() async {
    setState(() {
      _creating = true;
      _error = null;
    });
    try {
      final journey = await ref.read(journeyRepositoryProvider).createJourney(
            destinationName: _name.text.trim().isEmpty ? null : _name.text.trim(),
            latitude: _lat,
            longitude: _lng,
            expiresInMinutes: _durationMinutes,
          );
      if (mounted) context.go('/journeys/${journey['id']}/invited');
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _creating = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Create Journey')),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: Text(_error!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error)),
            ),
          TextField(
            controller: _name,
            decoration: const InputDecoration(
              labelText: 'Where are you going?',
              hintText: 'e.g. Ikeja City Mall',
            ),
          ),
          const SizedBox(height: 16),
          // Destination picker: long-press the map to choose a point (spec §22).
          // Mapbox map view is wired in the host live screen; the picker uses
          // coordinates fields for V1 simplicity with map integration point here.
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Destination coordinates',
                      style: Theme.of(context).textTheme.titleSmall),
                  const SizedBox(height: 8),
                  TextFormField(
                    initialValue: _lat.toStringAsFixed(6),
                    decoration: const InputDecoration(labelText: 'Latitude'),
                    keyboardType:
                        const TextInputType.numberWithOptions(decimal: true),
                    onChanged: (v) => _lat = double.tryParse(v) ?? _lat,
                  ),
                  const SizedBox(height: 8),
                  TextFormField(
                    initialValue: _lng.toStringAsFixed(6),
                    decoration: const InputDecoration(labelText: 'Longitude'),
                    keyboardType:
                        const TextInputType.numberWithOptions(decimal: true),
                    onChanged: (v) => _lng = double.tryParse(v) ?? _lng,
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          DropdownButtonFormField<int>(
            initialValue: _durationMinutes,
            decoration: const InputDecoration(labelText: 'Sharing window'),
            items: const [
              DropdownMenuItem(value: 30, child: Text('30 minutes')),
              DropdownMenuItem(value: 60, child: Text('1 hour')),
              DropdownMenuItem(value: 120, child: Text('2 hours')),
              DropdownMenuItem(value: 240, child: Text('4 hours')),
            ],
            onChanged: (v) => setState(() => _durationMinutes = v ?? 120),
          ),
          const SizedBox(height: 24),
          FilledButton(
            onPressed: _creating ? null : _create,
            child: _creating
                ? const SizedBox(
                    height: 20,
                    width: 20,
                    child: CircularProgressIndicator(strokeWidth: 2))
                : const Text('Create Journey'),
          ),
        ],
      ),
    );
  }
}

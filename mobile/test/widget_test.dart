import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:journeyng/features/home/presentation/home_screen.dart';

void main() {
  testWidgets('Home shows positioning copy and create action', (tester) async {
    await tester.pumpWidget(
      const ProviderScope(child: MaterialApp(home: HomeScreen())),
    );

    expect(find.textContaining('Share your journey'), findsOneWidget);
    expect(find.text('Create Journey'), findsOneWidget);
    expect(find.text('Log in / Create account'), findsOneWidget);
  });
}

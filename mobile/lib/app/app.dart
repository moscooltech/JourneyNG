import 'package:flutter/material.dart';

import 'router.dart';
import 'theme.dart';

class JourneyApp extends StatelessWidget {
  const JourneyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'JourneyNG',
      theme: AppTheme.light(),
      routerConfig: router,
      debugShowCheckedModeBanner: false,
    );
  }
}

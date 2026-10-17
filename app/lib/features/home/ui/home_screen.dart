import 'package:flutter/material.dart';
import 'package:signals/signals_flutter.dart';

import '../state/home_state.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'UpdateApply',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 12),
              SignalBuilder(
                builder: (context) {
                  return Text(
                    homeMessage.value,
                    style: Theme.of(context).textTheme.bodyLarge,
                  );
                },
              ),
              const SizedBox(height: 24),
              Text(
                'MVP: tailor-first. Profile + tailor screens come next.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

import 'package:flutter/material.dart';

import '../../../core/theme/app_theme.dart';
import 'auth_brand_mark.dart';

/// Centered auth column with the prototype enter motion (280ms rise).
class AuthShell extends StatefulWidget {
  const AuthShell({super.key, required this.child});

  final Widget child;

  @override
  State<AuthShell> createState() => _AuthShellState();
}

class _AuthShellState extends State<AuthShell>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 280),
  )..forward();

  late final Animation<double> _opacity = CurvedAnimation(
    parent: _controller,
    curve: const Cubic(0.22, 1, 0.36, 1),
  );

  late final Animation<Offset> _offset = Tween<Offset>(
    begin: const Offset(0, 8 / 400),
    end: Offset.zero,
  ).animate(_opacity);

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.grid * 3,
              vertical: AppSpacing.grid * 4,
            ),
            child: FadeTransition(
              opacity: _opacity,
              child: SlideTransition(
                position: _offset,
                child: ConstrainedBox(
                  constraints: const BoxConstraints(
                    maxWidth: AppSpacing.authColumn,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      const AuthBrandMark(),
                      const SizedBox(height: AppSpacing.grid * 3.5),
                      widget.child,
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

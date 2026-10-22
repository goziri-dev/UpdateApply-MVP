import 'package:flutter/material.dart';

import '../../../core/theme/app_theme.dart';

/// Pulse + elapsed timer while the interview mic is capturing (no live STT).
class InterviewRecordingIndicator extends StatefulWidget {
  const InterviewRecordingIndicator({super.key, required this.active});

  final bool active;

  @override
  State<InterviewRecordingIndicator> createState() =>
      _InterviewRecordingIndicatorState();
}

class _InterviewRecordingIndicatorState
    extends State<InterviewRecordingIndicator>
    with SingleTickerProviderStateMixin {
  late final AnimationController _pulse;
  DateTime? _startedAt;
  Duration _elapsed = Duration.zero;

  @override
  void initState() {
    super.initState();
    _pulse = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1100),
    );
    if (widget.active) _begin();
  }

  @override
  void didUpdateWidget(covariant InterviewRecordingIndicator oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.active && !oldWidget.active) {
      _begin();
    } else if (!widget.active && oldWidget.active) {
      _end();
    }
  }

  void _begin() {
    _startedAt = DateTime.now();
    _elapsed = Duration.zero;
    _pulse.repeat(reverse: true);
    _tick();
  }

  void _end() {
    _pulse.stop();
    _pulse.value = 0;
    _startedAt = null;
  }

  void _tick() {
    if (!mounted || !widget.active || _startedAt == null) return;
    setState(() {
      _elapsed = DateTime.now().difference(_startedAt!);
    });
    Future<void>.delayed(const Duration(seconds: 1), _tick);
  }

  @override
  void dispose() {
    _pulse.dispose();
    super.dispose();
  }

  String get _timerLabel {
    final total = _elapsed.inSeconds;
    final m = (total ~/ 60).toString().padLeft(2, '0');
    final s = (total % 60).toString().padLeft(2, '0');
    return '$m:$s';
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.active) return const SizedBox.shrink();

    final scheme = Theme.of(context).colorScheme;
    final type = Theme.of(context).textTheme;

    return AnimatedBuilder(
      animation: _pulse,
      builder: (context, child) {
        final t = Curves.easeInOut.transform(_pulse.value);
        return Row(
          children: [
            SizedBox(
              width: 28,
              height: 28,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  Transform.scale(
                    scale: 1 + (t * 0.45),
                    child: Container(
                      width: 22,
                      height: 22,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: scheme.error.withValues(alpha: 0.18 + t * 0.12),
                      ),
                    ),
                  ),
                  Container(
                    width: 10,
                    height: 10,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: scheme.error,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: AppSpacing.grid),
            Text(
              'Recording $_timerLabel',
              style: type.bodyMedium?.copyWith(
                color: scheme.error,
                fontWeight: FontWeight.w600,
                fontFeatures: const [FontFeature.tabularFigures()],
              ),
            ),
          ],
        );
      },
    );
  }
}

import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:signals_flutter/signals_flutter.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../state/onboarding_state.dart';
import '../widgets/onboarding_feedback.dart';
import '../widgets/onboarding_shell.dart';

class OnboardingUploadScreen extends StatefulWidget {
  const OnboardingUploadScreen({super.key});

  @override
  State<OnboardingUploadScreen> createState() => _OnboardingUploadScreenState();
}

class _OnboardingUploadScreenState extends State<OnboardingUploadScreen> {
  String? _fileName;
  int? _fileSize;
  Uint8List? _bytes;

  static const _maxBytes = 10 * 1024 * 1024;

  Future<void> _pick() async {
    clearOnboardingFeedback();
    final files = await FilePicker.pickFiles(
      type: FileType.custom,
      allowedExtensions: const ['pdf'],
    );
    if (files.isEmpty) return;
    final file = files.first;
    final name = file.name;
    late final Uint8List bytes;
    try {
      bytes = await file.readAsBytes();
    } on Object {
      setOnboardingError('Could not read that file. Try another PDF.');
      return;
    }
    final isPdf = name.toLowerCase().endsWith('.pdf');
    if (!isPdf) {
      setState(() {
        _fileName = null;
        _fileSize = null;
        _bytes = null;
      });
      setOnboardingError(
        "That file isn't a PDF. Upload a PDF resume (LinkedIn export works).",
      );
      return;
    }
    if (bytes.length > _maxBytes) {
      setState(() {
        _fileName = null;
        _fileSize = null;
        _bytes = null;
      });
      setOnboardingError(
        'This file is over 10MB. Export a leaner PDF and try again.',
      );
      return;
    }
    setState(() {
      _fileName = name;
      _fileSize = bytes.length;
      _bytes = bytes;
    });
  }

  Future<void> _upload() async {
    final name = _fileName;
    final bytes = _bytes;
    if (name == null || bytes == null) {
      setOnboardingError(
        "Choose a PDF resume to continue. Onboarding can't be skipped.",
      );
      return;
    }
    onboardingBusy.value = true;
    clearOnboardingFeedback();
    try {
      await onboardingService.uploadPdf(filename: name, bytes: bytes);
      await refreshOnboardingGate(statusHint: 'in_progress');
      if (!mounted) return;
      context.go('/onboarding/parsing');
    } on DioException catch (e) {
      setOnboardingError(_dioMessage(e));
    } on Object catch (e) {
      setOnboardingError(e.toString());
    } finally {
      onboardingBusy.value = false;
    }
  }

  String _dioMessage(DioException e) {
    final detail = e.response?.data;
    if (detail is Map && detail['detail'] != null) {
      return detail['detail'].toString();
    }
    return e.message ?? 'Upload failed';
  }

  String _formatBytes(int n) {
    if (n < 1024) return '$n B';
    if (n < 1024 * 1024) return '${(n / 1024).toFixed(1)} KB';
    return '${(n / (1024 * 1024)).toFixed(1)} MB';
  }

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;
    final colors = context.appColors;
    final hasFile = _fileName != null;

    return OnboardingShell(
      stepLabel: '1 / 5',
      caption: 'Your profile takes shape as you go',
      backEnabled: false,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text("Let's build your profile", style: type.headlineMedium),
          const SizedBox(height: AppSpacing.grid * 1.5),
          Text(
            "Upload any existing resume. We'll extract your basics, history, "
            'and projects — then talk through each role and project in a '
            'calm chat so your profile reflects what actually happened.',
            style: type.bodyMedium?.copyWith(
              color: colors.muted,
              height: 1.45,
              fontWeight: FontWeight.w400,
            ),
          ),
          const SizedBox(height: AppSpacing.grid * 2.5),
          const OnboardingFeedbackBanner(),
          Material(
            color: scheme.surfaceContainerHighest,
            borderRadius: BorderRadius.circular(16),
            child: InkWell(
              onTap: hasFile ? null : _pick,
              borderRadius: BorderRadius.circular(16),
              child: CustomPaint(
                painter: _DashedBorderPainter(color: colors.oauthBorder),
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.grid * 3,
                    vertical: AppSpacing.grid * 4,
                  ),
                  child: hasFile
                      ? Row(
                          children: [
                            Container(
                              width: 48,
                              height: 48,
                              alignment: Alignment.center,
                              decoration: BoxDecoration(
                                color: scheme.primary.withValues(alpha: 0.12),
                                borderRadius: BorderRadius.circular(10),
                              ),
                              child: Text(
                                'PDF',
                                style: type.labelSmall?.copyWith(
                                  color: scheme.primary,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ),
                            const SizedBox(width: AppSpacing.grid * 2),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(_fileName!, style: type.bodyLarge),
                                  Text(
                                    '${_formatBytes(_fileSize ?? 0)} · ready to upload',
                                    style: type.bodySmall?.copyWith(
                                      color: colors.muted,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            TextButton(
                              onPressed: () {
                                setState(() {
                                  _fileName = null;
                                  _fileSize = null;
                                  _bytes = null;
                                });
                              },
                              child: const Text('Remove'),
                            ),
                          ],
                        )
                      : Column(
                          children: [
                            Text(
                              '+',
                              style: type.headlineMedium?.copyWith(
                                color: colors.muted,
                              ),
                            ),
                            const SizedBox(height: AppSpacing.grid),
                            Text(
                              'Choose a PDF or drag and drop it here',
                              textAlign: TextAlign.center,
                              style: type.titleMedium,
                            ),
                            const SizedBox(height: AppSpacing.grid),
                            Text(
                              'PDF only · max 10MB · LinkedIn export recommended',
                              textAlign: TextAlign.center,
                              style: type.bodySmall?.copyWith(
                                color: colors.muted,
                              ),
                            ),
                            const SizedBox(height: AppSpacing.grid * 2),
                            OutlinedButton(
                              onPressed: _pick,
                              style: OutlinedButton.styleFrom(
                                foregroundColor: scheme.onSurface,
                                side: BorderSide(color: colors.oauthBorder),
                                shape: const StadiumBorder(),
                                minimumSize: const Size(140, 44),
                              ),
                              child: const Text('Browse File'),
                            ),
                          ],
                        ),
                ),
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.grid * 3),
          SignalBuilder(
            builder: (context) {
              final busy = onboardingBusy.value;
              return FilledButton(
                onPressed: busy ? null : _upload,
                child: busy
                    ? SizedBox(
                        height: 18,
                        width: 18,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: scheme.onPrimary,
                        ),
                      )
                    : const Text('Upload resume'),
              );
            },
          ),
        ],
      ),
    );
  }
}

extension on double {
  String toFixed(int fractionDigits) => toStringAsFixed(fractionDigits);
}

class _DashedBorderPainter extends CustomPainter {
  _DashedBorderPainter({required this.color});

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = 1.5
      ..style = PaintingStyle.stroke;
    const dash = 6.0;
    const gap = 4.0;
    final path = Path()
      ..addRRect(
        RRect.fromRectAndRadius(Offset.zero & size, const Radius.circular(16)),
      );
    for (final metric in path.computeMetrics()) {
      var distance = 0.0;
      while (distance < metric.length) {
        final next = distance + dash;
        canvas.drawPath(metric.extractPath(distance, next), paint);
        distance = next + gap;
      }
    }
  }

  @override
  bool shouldRepaint(covariant _DashedBorderPainter oldDelegate) =>
      oldDelegate.color != color;
}

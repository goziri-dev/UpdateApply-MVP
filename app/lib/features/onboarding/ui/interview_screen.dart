import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../services/interview_speech.dart';
import '../state/onboarding_state.dart';
import '../widgets/onboarding_feedback.dart';
import '../widgets/onboarding_shell.dart';

/// Guided interview UI with browser mic + Web Speech API STT (typed fallback).
class OnboardingInterviewScreen extends StatefulWidget {
  const OnboardingInterviewScreen({super.key});

  @override
  State<OnboardingInterviewScreen> createState() =>
      _OnboardingInterviewScreenState();
}

class _OnboardingInterviewScreenState extends State<OnboardingInterviewScreen> {
  final _transcriptCtrl = TextEditingController();
  final _speech = InterviewSpeech();

  bool _loading = true;
  bool _submitting = false;
  bool _recording = false;
  bool _micDenied = false;
  bool _speechUnsupported = false;

  String? _itemId;
  String? _itemKind;
  String? _itemLabel;
  String? _question;
  int _qIndex = 0;
  int _qTotal = 0;
  List<String> _coverage = [];
  List<String> _hits = [];
  List<Map<String, dynamic>> _queue = [];

  @override
  void initState() {
    super.initState();
    _speechUnsupported = !_speech.isSupported;
    _load();
  }

  @override
  void dispose() {
    _speech.dispose();
    _transcriptCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    clearOnboardingFeedback();
    try {
      final data = await onboardingService.interviewState();
      if (!mounted) return;
      if (data['interview_complete'] == true) {
        context.go('/onboarding/review');
        return;
      }
      _applyState(data);
    } on DioException catch (e) {
      setOnboardingError(_dioMessage(e));
    } on Object catch (e) {
      setOnboardingError(e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _applyState(Map<String, dynamic> data) {
    setState(() {
      _itemId = data['item_id'] as String?;
      _itemKind = data['item_kind'] as String?;
      _itemLabel = data['item_label'] as String?;
      _question = data['question'] as String?;
      _qIndex = (data['question_index'] as num?)?.toInt() ?? 0;
      _qTotal = (data['question_total'] as num?)?.toInt() ?? 0;
      _coverage = (data['coverage'] as List? ?? []).map((e) => '$e').toList();
      _hits = (data['coverage_hits'] as List? ?? []).map((e) => '$e').toList();
      _queue = (data['queue'] as List? ?? [])
          .whereType<Map>()
          .map((e) => Map<String, dynamic>.from(e))
          .toList();
      _transcriptCtrl.clear();
      _recording = false;
    });
  }

  Future<void> _submit({required bool forceDone}) async {
    if (_recording) {
      await _speech.stop();
    }
    final itemId = _itemId;
    if (itemId == null) return;
    final text = _transcriptCtrl.text.trim();
    if (text.isEmpty && !forceDone) {
      setOnboardingError(
        'Add a short answer (record or type) before continuing.',
      );
      return;
    }
    setState(() => _submitting = true);
    clearOnboardingFeedback();
    try {
      final res = await onboardingService.interviewTurn(
        itemId: itemId,
        transcript: text,
        forceDone: forceDone,
      );
      if (!mounted) return;
      if (res['interview_complete'] == true) {
        context.go('/onboarding/review');
        return;
      }
      if (res['item_complete'] == true) {
        await _load();
        return;
      }
      setState(() {
        _question = res['question'] as String?;
        _qIndex = (res['question_index'] as num?)?.toInt() ?? _qIndex;
        _qTotal = (res['question_total'] as num?)?.toInt() ?? _qTotal;
        _coverage = (res['coverage'] as List? ?? _coverage)
            .map((e) => '$e')
            .toList();
        _hits = (res['coverage_hits'] as List? ?? []).map((e) => '$e').toList();
        _transcriptCtrl.clear();
      });
    } on DioException catch (e) {
      setOnboardingError(_dioMessage(e));
    } on Object catch (e) {
      setOnboardingError(e.toString());
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  Future<void> _toggleMic() async {
    if (_recording) {
      await _speech.stop();
      return;
    }

    if (_micDenied) {
      setOnboardingError(
        'Microphone permission was denied. Type your answer in the box — '
        'voice is preferred, but text works. Re-enable mic in the browser '
        'site settings, then tap the mic again.',
      );
      return;
    }

    if (_speechUnsupported || !_speech.isSupported) {
      setState(() => _speechUnsupported = true);
      setOnboardingError(
        'Voice dictation isn’t available in this browser. Type your answer '
        'below — Chrome or Edge on HTTPS/localhost work best.',
      );
      return;
    }

    clearOnboardingFeedback();
    final result = await _speech.start(
      seedTranscript: _transcriptCtrl.text,
      onUpdate: (update) {
        if (!mounted) return;
        _transcriptCtrl.value = TextEditingValue(
          text: update.transcript,
          selection: TextSelection.collapsed(offset: update.transcript.length),
        );
      },
      onEnded: ({String? error}) {
        if (!mounted) return;
        setState(() => _recording = false);
        if (error == 'not-allowed' || error == 'service-not-allowed') {
          setState(() => _micDenied = true);
          setOnboardingError(
            'Microphone permission was denied. Type your answer in the box — '
            'voice is preferred, but text works. Re-enable mic in the browser '
            'site settings, then tap the mic again.',
          );
          return;
        }
        if (error != null && error != 'aborted' && error != 'no-speech') {
          setOnboardingError(
            'Voice recognition paused ($error). You can type or tap the mic '
            'to try again.',
          );
        }
      },
    );

    if (!mounted) return;

    switch (result) {
      case InterviewSpeechStart.started:
        setState(() {
          _recording = true;
          _micDenied = false;
        });
        setOnboardingInfo('Listening… tap the mic when you’re done.');
      case InterviewSpeechStart.denied:
        setState(() {
          _micDenied = true;
          _recording = false;
        });
        setOnboardingError(
          'Microphone permission was denied. Type your answer instead.',
        );
      case InterviewSpeechStart.unsupported:
        setState(() {
          _speechUnsupported = true;
          _recording = false;
        });
        setOnboardingError(
          'Voice dictation isn’t available in this browser. Type your answer '
          'below.',
        );
      case InterviewSpeechStart.failed:
        setState(() => _recording = false);
        setOnboardingError(
          'Couldn’t start the microphone. Check browser permissions, use '
          'HTTPS or localhost, then try again — or type your answer.',
        );
    }
  }

  String _dioMessage(DioException e) {
    final detail = e.response?.data;
    if (detail is Map && detail['detail'] != null) {
      return detail['detail'].toString();
    }
    return e.message ?? 'Request failed';
  }

  String get _micHint {
    if (_recording) return 'Recording… tap to stop';
    if (_micDenied) return 'Mic blocked — type your answer';
    if (_speechUnsupported) return 'Voice unavailable — type your answer';
    return 'Tap to record your answer';
  }

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;
    final colors = context.appColors;
    final isRole = _itemKind != 'project';

    return OnboardingShell(
      stepLabel: '3 / 5',
      caption: 'Voice fills in what the PDF missed',
      onBack: () => context.go('/onboarding/upload'),
      child: _loading
          ? const Padding(
              padding: EdgeInsets.only(top: 48),
              child: Center(child: CircularProgressIndicator()),
            )
          : Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  isRole
                      ? 'Tell us about this role'
                      : 'Tell us about this project',
                  style: type.headlineMedium,
                ),
                const SizedBox(height: AppSpacing.grid * 1.5),
                Text(
                  'Resume bullets are a checklist. Your voice is the evidence. '
                  'Aim for a couple of minutes — say “that’s all” when you’re done.',
                  style: type.bodyMedium?.copyWith(
                    color: colors.muted,
                    height: 1.45,
                    fontWeight: FontWeight.w400,
                  ),
                ),
                const SizedBox(height: AppSpacing.grid * 2),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: _queue.map((q) {
                    final state = q['state'] as String? ?? 'todo';
                    final label = q['label'] as String? ?? '';
                    final color = switch (state) {
                      'done' => scheme.primary,
                      'active' => scheme.onSurface,
                      _ => colors.muted,
                    };
                    return Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 6,
                      ),
                      decoration: BoxDecoration(
                        color: scheme.surfaceContainerHighest,
                        borderRadius: BorderRadius.circular(999),
                        border: Border.all(
                          color: state == 'active'
                              ? scheme.primary
                              : colors.oauthBorder,
                        ),
                      ),
                      child: Text(
                        label,
                        style: type.bodySmall?.copyWith(color: color),
                      ),
                    );
                  }).toList(),
                ),
                const SizedBox(height: AppSpacing.grid * 2),
                const OnboardingFeedbackBanner(),
                DecoratedBox(
                  decoration: BoxDecoration(
                    color: scheme.surfaceContainerHighest,
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(AppSpacing.grid * 3),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                _itemLabel ?? '',
                                style: type.bodyLarge,
                              ),
                            ),
                            Text(
                              'Follow-up ${_qIndex + 1} of ~$_qTotal',
                              style: type.bodySmall?.copyWith(
                                color: colors.muted,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: AppSpacing.grid * 2),
                        DecoratedBox(
                          decoration: BoxDecoration(
                            color: Colors.white,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Padding(
                            padding: const EdgeInsets.all(AppSpacing.grid * 2),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'UpdateApply',
                                  style: type.labelSmall?.copyWith(
                                    color: scheme.primary,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  _question ?? '',
                                  style: type.bodyLarge?.copyWith(height: 1.4),
                                ),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(height: AppSpacing.grid * 2),
                        Row(
                          children: [
                            Material(
                              color: _recording ? scheme.error : scheme.primary,
                              shape: const CircleBorder(),
                              child: InkWell(
                                customBorder: const CircleBorder(),
                                onTap: _submitting ? null : _toggleMic,
                                child: SizedBox(
                                  width: 56,
                                  height: 56,
                                  child: Icon(
                                    _recording ? Icons.stop : Icons.mic,
                                    color: Colors.white,
                                  ),
                                ),
                              ),
                            ),
                            const SizedBox(width: AppSpacing.grid * 2),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(_micHint, style: type.bodyLarge),
                                  Text(
                                    'Or type below. Coverage checklist helps us know when this item is done.',
                                    style: type.bodySmall?.copyWith(
                                      color: colors.muted,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: AppSpacing.grid * 2),
                        TextField(
                          controller: _transcriptCtrl,
                          maxLines: 4,
                          decoration: InputDecoration(
                            hintText: 'Your answer appears here…',
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                            ),
                            enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(12),
                              borderSide: BorderSide(color: colors.oauthBorder),
                            ),
                          ),
                        ),
                        const SizedBox(height: AppSpacing.grid * 2),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: _coverage.map((c) {
                            final hit = _hits.contains(c);
                            return Chip(
                              label: Text(c),
                              backgroundColor: hit
                                  ? scheme.primary.withValues(alpha: 0.12)
                                  : Colors.white,
                              side: BorderSide(
                                color: hit
                                    ? scheme.primary
                                    : colors.oauthBorder,
                              ),
                            );
                          }).toList(),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: AppSpacing.grid * 3),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: _submitting
                            ? null
                            : () => _submit(forceDone: true),
                        style: OutlinedButton.styleFrom(
                          minimumSize: const Size.fromHeight(
                            AppSpacing.controlHeight,
                          ),
                          shape: const StadiumBorder(),
                        ),
                        child: Text(
                          'Done with this ${isRole ? 'role' : 'project'}',
                        ),
                      ),
                    ),
                    const SizedBox(width: AppSpacing.grid * 1.5),
                    Expanded(
                      child: FilledButton(
                        onPressed: _submitting
                            ? null
                            : () => _submit(forceDone: false),
                        child: _submitting
                            ? SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: scheme.onPrimary,
                                ),
                              )
                            : Text(
                                _qIndex + 1 >= _qTotal
                                    ? 'Next item'
                                    : 'Next follow-up',
                              ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
    );
  }
}

import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../../applications/services/applications_service.dart';
import '../../onboarding/services/interview_audio.dart';
import '../../onboarding/state/onboarding_state.dart';
import '../../onboarding/widgets/interview_recording_indicator.dart';
import '../services/resume_service.dart';
import '../state/master_resume_state.dart';
import '../widgets/resume_document_form.dart';
import 'resume_deepen_screen.dart';

enum ResumeEditTarget { master, application }

enum _HarnessMode { edit, ask }

extension on _HarnessMode {
  String get apiValue => switch (this) {
    _HarnessMode.edit => 'edit',
    _HarnessMode.ask => 'ask',
  };

  String get label => switch (this) {
    _HarnessMode.edit => 'Edit',
    _HarnessMode.ask => 'Ask',
  };
}

class _HistoryEntry {
  const _HistoryEntry({
    required this.role,
    required this.text,
    required this.mode,
  });

  final String role; // you | agent
  final String text;
  final String mode;
}

/// Shared hybrid editor for master or tailored application resumes.
class ResumeEditScreen extends StatefulWidget {
  const ResumeEditScreen.master({super.key})
    : target = ResumeEditTarget.master,
      applicationId = null;

  const ResumeEditScreen.application({super.key, required this.applicationId})
    : target = ResumeEditTarget.application;

  final ResumeEditTarget target;
  final String? applicationId;

  @override
  State<ResumeEditScreen> createState() => _ResumeEditScreenState();
}

class _ResumeEditScreenState extends State<ResumeEditScreen> {
  final _resumeService = ResumeService();
  final _applicationsService = ApplicationsService();
  final _instruction = TextEditingController();
  final _audio = InterviewAudio();
  ResumeDocumentFormState? _formState;

  bool _loading = true;
  bool _saving = false;
  bool _proposing = false;
  bool _recording = false;
  bool _transcribing = false;
  bool _micDenied = false;
  bool _audioUnsupported = false;
  String _seedBeforeRecord = '';
  String? _error;
  String? _banner;
  String? _voiceInfo;
  Map<String, dynamic>? _document;
  Map<String, dynamic>? _baselineBeforeProposal;
  String? _sessionId;
  String? _pendingOutcome;
  _HarnessMode _mode = _HarnessMode.edit;
  final List<_HistoryEntry> _history = [];
  int _formGen = 0;

  /// Remount the form via [ValueKey] (not GlobalKey — regenerating GlobalKey
  /// left an empty form slot / broke hit-testing on Flutter web).
  void _replaceFormDocument(Map<String, dynamic> doc) {
    _document = doc;
    _formGen++;
    _formState = null;
  }

  ResumeDocumentFormState? get _form => _formState;

  @override
  void initState() {
    super.initState();
    _audioUnsupported = !_audio.isSupported;
    _load();
  }

  @override
  void dispose() {
    final sid = _sessionId;
    if (sid != null && sid.isNotEmpty) {
      // Best-effort; do not block dispose.
      unawaited(_resumeService.clearEditSession(sid));
    }
    _audio.dispose();
    _instruction.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
      _banner = null;
    });
    try {
      final Map<String, dynamic> doc;
      if (widget.target == ResumeEditTarget.master) {
        doc = await _resumeService.getDocument();
      } else {
        final id = widget.applicationId ?? '';
        final detail = await _applicationsService.get(id);
        final resume = detail['resume'];
        if (resume is! Map) {
          throw StateError('Application has no resume document');
        }
        doc = Map<String, dynamic>.from(resume);
      }
      if (!mounted) return;
      setState(() {
        _replaceFormDocument(doc);
        _loading = false;
      });
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = _dioMessage(e);
        _loading = false;
      });
    } on Object catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
        _loading = false;
      });
    }
  }

  String _dioMessage(DioException e) {
    final detail = e.response?.data;
    if (detail is Map && detail['detail'] != null) {
      return detail['detail'].toString();
    }
    return e.message ?? 'Request failed';
  }

  Future<void> _persist(Map<String, dynamic> doc) async {
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      late final Map<String, dynamic> saved;
      if (widget.target == ResumeEditTarget.master) {
        saved = await _resumeService.putDocument(doc);
      } else {
        final id = widget.applicationId ?? '';
        final updated = await _applicationsService.patch(id, resume: doc);
        final resume = updated['resume'];
        saved = resume is Map ? Map<String, dynamic>.from(resume) : doc;
      }
      if (!mounted) return;
      setState(() {
        _replaceFormDocument(saved);
        _banner = null;
        _baselineBeforeProposal = null;
        _saving = false;
      });
      if (widget.target == ResumeEditTarget.master) {
        bumpMasterResumeEpoch();
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            widget.target == ResumeEditTarget.master
                ? 'Master resume saved'
                : 'Application resume saved',
          ),
        ),
      );
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = _dioMessage(e);
        _saving = false;
      });
    } on Object catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
        _saving = false;
      });
    }
  }

  Future<void> _save() async {
    final form = _form;
    if (form == null) return;
    await _persist(form.toDocument());
  }

  Future<void> _resetSession() async {
    final sid = _sessionId;
    if (sid != null && sid.isNotEmpty) {
      try {
        await _resumeService.clearEditSession(sid);
      } on Object {
        // Ignore — local clear still proceeds.
      }
    }
    if (!mounted) return;
    setState(() {
      _sessionId = null;
      _pendingOutcome = null;
      _baselineBeforeProposal = null;
      _history.clear();
      _banner = 'Chat cleared — next message starts fresh.';
      _error = null;
    });
  }

  Future<void> _toggleMic() async {
    if (_transcribing || _proposing || _saving) return;

    if (_recording) {
      await _stopAndTranscribe();
      return;
    }

    if (_micDenied) {
      setState(
        () => _error =
            'Microphone permission was denied. Type your ${_mode == _HarnessMode.ask ? 'question' : 'instruction'} instead.',
      );
      return;
    }

    if (_audioUnsupported || !_audio.isSupported) {
      setState(() {
        _audioUnsupported = true;
        _error =
            'Voice isn’t available here. Type your ${_mode == _HarnessMode.ask ? 'question' : 'instruction'} instead.';
      });
      return;
    }

    setState(() {
      _error = null;
      _voiceInfo = null;
    });
    _seedBeforeRecord = _instruction.text.trim();
    final result = await _audio.start();
    if (!mounted) return;

    switch (result) {
      case InterviewAudioStart.started:
        setState(() {
          _recording = true;
          _micDenied = false;
          _voiceInfo = 'Recording… tap stop when you’re done.';
        });
      case InterviewAudioStart.denied:
        setState(() {
          _micDenied = true;
          _recording = false;
          _error =
              'Microphone permission was denied. Type your ${_mode == _HarnessMode.ask ? 'question' : 'instruction'} instead.';
        });
      case InterviewAudioStart.unsupported:
        setState(() {
          _audioUnsupported = true;
          _recording = false;
          _error =
              'Voice isn’t available here. Type your ${_mode == _HarnessMode.ask ? 'question' : 'instruction'} instead.';
        });
      case InterviewAudioStart.failed:
        setState(() {
          _recording = false;
          _error =
              'Couldn’t start the mic. Type your ${_mode == _HarnessMode.ask ? 'question' : 'instruction'} instead.';
        });
    }
  }

  Future<void> _stopAndTranscribe() async {
    if (!_recording) return;
    setState(() {
      _recording = false;
      _transcribing = true;
      _voiceInfo = 'Transcribing…';
      _error = null;
    });

    InterviewAudioClip? clip;
    try {
      clip = await _audio.stop();
    } on Object {
      clip = null;
    }

    if (!mounted) return;

    if (clip == null || clip.bytes.isEmpty) {
      setState(() {
        _transcribing = false;
        _voiceInfo = null;
        _error = 'No audio captured. Try again or type instead.';
      });
      return;
    }

    try {
      final transcript = await onboardingService.transcribeAudio(
        bytes: clip.bytes,
        filename: clip.filename,
      );
      if (!mounted) return;
      final merged = [
        if (_seedBeforeRecord.isNotEmpty) _seedBeforeRecord,
        transcript,
      ].join(' ').trim();
      _instruction.value = TextEditingValue(
        text: merged,
        selection: TextSelection.collapsed(offset: merged.length),
      );
      setState(() {
        _voiceInfo = 'Transcript ready — edit if needed, then continue.';
        _error = null;
      });
    } on DioException catch (e) {
      setState(() {
        _voiceInfo = null;
        _error = '${_dioMessage(e)} You can type instead.';
      });
    } on Object catch (e) {
      setState(() {
        _voiceInfo = null;
        _error = 'Transcription failed ($e). Type instead.';
      });
    } finally {
      if (mounted) setState(() => _transcribing = false);
    }
  }

  Future<void> _propose() async {
    final form = _form;
    if (form == null) return;
    if (_recording) await _stopAndTranscribe();
    if (_transcribing) return;
    final instruction = _instruction.text.trim();
    if (instruction.isEmpty) {
      setState(
        () => _error = _mode == _HarnessMode.ask
            ? 'Ask a question first.'
            : 'Describe what to change first.',
      );
      return;
    }
    final current = form.toDocument();
    // Continuing with a loaded proposal implies keeping the form as-is.
    final outcomeForTurn =
        _pendingOutcome ??
        (_baselineBeforeProposal != null ? 'accepted' : null);
    setState(() {
      _proposing = true;
      _error = null;
      _voiceInfo = null;
    });
    try {
      final result = await _resumeService.proposeEdit(
        resume: current,
        instruction: instruction,
        mode: _mode.apiValue,
        sessionId: _sessionId,
        priorOutcome: outcomeForTurn,
      );
      final proposed = result['resume'];
      if (proposed is! Map) {
        throw StateError('Empty proposal from server');
      }
      final doc = Map<String, dynamic>.from(proposed);
      final sid = result['session_id']?.toString();
      final detail = result['detail'] as String?;
      final applied = result['applied'] != false;
      final confidence = result['confidence'];
      if (!mounted) return;

      final historyYou = _HistoryEntry(
        role: 'you',
        text: instruction,
        mode: _mode.label,
      );
      final confBit = confidence is num
          ? '\n\nConfidence: ${(confidence * 100).round()}%.'
          : '';
      final baseText = (detail != null && detail.trim().isNotEmpty)
          ? detail.trim()
          : (applied ? 'Proposed changes loaded.' : 'Answer ready.');
      final agentText = '$baseText$confBit';
      final historyAgent = _HistoryEntry(
        role: 'agent',
        text: agentText,
        mode: _mode.label,
      );

      setState(() {
        _sessionId = (sid != null && sid.isNotEmpty) ? sid : _sessionId;
        _pendingOutcome = null;
        _history.add(historyYou);
        _history.add(historyAgent);
        _proposing = false;
        // Model text lives only in the transcript — no duplicate banner.
        _banner = null;
        if (applied) {
          _baselineBeforeProposal = current;
          _replaceFormDocument(doc);
        } else {
          _baselineBeforeProposal = null;
        }
      });
      _instruction.clear();
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = _dioMessage(e);
        _proposing = false;
      });
    } on Object catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
        _proposing = false;
      });
    }
  }

  void _acceptProposal() {
    if (_baselineBeforeProposal == null) return;
    setState(() {
      _pendingOutcome = 'accepted';
      _baselineBeforeProposal = null;
      _banner = 'Kept in the form. Save when ready.';
    });
  }

  void _rejectProposal() {
    final baseline = _baselineBeforeProposal;
    if (baseline == null) return;
    setState(() {
      _pendingOutcome = 'rejected';
      _replaceFormDocument(baseline);
      _baselineBeforeProposal = null;
      _banner = 'Proposal discarded — form restored. Continue or try again.';
    });
  }

  void _goBack() {
    if (context.canPop()) {
      context.pop();
      return;
    }
    if (widget.target == ResumeEditTarget.application &&
        widget.applicationId != null) {
      context.go('/applications/${widget.applicationId}');
      return;
    }
    context.go('/');
  }

  Future<void> _deepen({required String section, required int index}) async {
    final form = _form;
    if (form == null) return;
    final current = form.toDocument();
    final result = await context.push<Map<String, dynamic>>(
      '/resume/deepen',
      extra: ResumeDeepenArgs(resume: current, section: section, index: index),
    );
    if (!mounted || result == null) return;
    setState(() {
      _replaceFormDocument(result);
      _banner = 'Added to the form. Review, then save.';
      _error = null;
      _baselineBeforeProposal = null;
    });
  }

  String get _helperCopy => switch (_mode) {
    _HarnessMode.edit =>
      'Speak or type a change to your resume. We won’t invent details.',
    _HarnessMode.ask => 'Speak or type a question about your resume. Nothing changes until you switch to Edit.',
  };

  String get _ctaLabel => switch (_mode) {
    _HarnessMode.edit => 'Propose edits',
    _HarnessMode.ask => 'Ask',
  };

  String get _micHint {
    if (_transcribing) return 'Transcribing…';
    if (_recording) return 'Recording… tap to stop';
    if (_micDenied) return 'Mic blocked — type instead';
    if (_audioUnsupported) return 'Voice unavailable — type instead';
    return _mode == _HarnessMode.ask
        ? 'Tap to record your question'
        : 'Tap to record your instruction';
  }

  bool get _micBusy => _proposing || _saving || _transcribing;
  bool get _inputBusy => _proposing || _saving || _recording || _transcribing;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final scheme = Theme.of(context).colorScheme;
    final isMaster = widget.target == ResumeEditTarget.master;
    final title = isMaster ? 'Edit master resume' : 'Edit tailored resume';
    final subtitle = isMaster
        ? 'Update your roles and projects, then save.'
        : 'Changes apply to this tailored resume only.';

    return Scaffold(
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.grid * 3,
            AppSpacing.grid * 2,
            AppSpacing.grid * 3,
            AppSpacing.grid * 6,
          ),
          children: [
            Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 560),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Align(
                      alignment: Alignment.centerLeft,
                      child: TextButton(
                        onPressed: _goBack,
                        style: TextButton.styleFrom(
                          foregroundColor: scheme.onSurface,
                          padding: EdgeInsets.zero,
                          minimumSize: Size.zero,
                          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        ),
                        child: Text(isMaster ? '← Home' : '← Application'),
                      ),
                    ),
                    const SizedBox(height: AppSpacing.grid * 2),
                    if (_loading)
                      const Padding(
                        padding: EdgeInsets.symmetric(vertical: 48),
                        child: Center(child: CircularProgressIndicator()),
                      )
                    else if (_error != null && _document == null)
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Text(title, style: type.headlineMedium),
                          const SizedBox(height: AppSpacing.grid * 1.5),
                          DecoratedBox(
                            decoration: BoxDecoration(
                              color: scheme.errorContainer,
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Padding(
                              padding: const EdgeInsets.all(
                                AppSpacing.grid * 2,
                              ),
                              child: Text(
                                _error!,
                                style: type.bodyMedium?.copyWith(
                                  color: scheme.error,
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(height: AppSpacing.grid * 2),
                          FilledButton(
                            onPressed: _load,
                            child: const Text('Try again'),
                          ),
                        ],
                      )
                    else ...[
                      Text(title, style: type.headlineMedium),
                      const SizedBox(height: AppSpacing.grid * 1.5),
                      Text(
                        subtitle,
                        style: type.bodyMedium?.copyWith(
                          color: colors.muted,
                          height: 1.45,
                          fontWeight: FontWeight.w400,
                        ),
                      ),
                      if (_error != null) ...[
                        const SizedBox(height: AppSpacing.grid * 2),
                        DecoratedBox(
                          decoration: BoxDecoration(
                            color: scheme.errorContainer,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Padding(
                            padding: const EdgeInsets.all(AppSpacing.grid * 2),
                            child: Text(
                              _error!,
                              style: type.bodyMedium?.copyWith(
                                color: scheme.error,
                              ),
                            ),
                          ),
                        ),
                      ],
                      if (_banner != null) ...[
                        const SizedBox(height: AppSpacing.grid * 2),
                        DecoratedBox(
                          decoration: BoxDecoration(
                            color: scheme.surfaceContainerHighest,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Padding(
                            padding: const EdgeInsets.all(AppSpacing.grid * 2),
                            child: Text(
                              _banner!,
                              style: type.bodyMedium?.copyWith(height: 1.4),
                            ),
                          ),
                        ),
                      ],
                      const SizedBox(height: AppSpacing.grid * 3),
                      Row(
                        children: [
                          Expanded(
                            child: Text('Agent', style: type.titleMedium),
                          ),
                          TextButton(
                            onPressed: _inputBusy ? null : _resetSession,
                            child: const Text('Reset chat'),
                          ),
                        ],
                      ),
                      const SizedBox(height: AppSpacing.grid),
                      Wrap(
                        spacing: AppSpacing.grid,
                        runSpacing: AppSpacing.grid,
                        children: [
                          for (final m in _HarnessMode.values)
                            ChoiceChip(
                              label: Text(m.label),
                              selected: _mode == m,
                              onSelected: _inputBusy
                                  ? null
                                  : (selected) {
                                      if (selected) {
                                        setState(() => _mode = m);
                                      }
                                    },
                            ),
                        ],
                      ),
                      const SizedBox(height: AppSpacing.grid),
                      Text(
                        _helperCopy,
                        style: type.bodySmall?.copyWith(
                          color: colors.muted,
                          height: 1.4,
                          fontWeight: FontWeight.w400,
                        ),
                      ),
                      if (_history.isNotEmpty || _proposing) ...[
                        const SizedBox(height: AppSpacing.grid * 2),
                        DecoratedBox(
                          decoration: BoxDecoration(
                            border: Border.all(color: scheme.outlineVariant),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Padding(
                            padding: const EdgeInsets.all(AppSpacing.grid * 2),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                for (var i = 0; i < _history.length; i++) ...[
                                  if (i > 0)
                                    const SizedBox(
                                      height: AppSpacing.grid * 1.5,
                                    ),
                                  _ChatBubble(entry: _history[i]),
                                ],
                                if (_proposing) ...[
                                  if (_history.isNotEmpty)
                                    const SizedBox(
                                      height: AppSpacing.grid * 1.5,
                                    ),
                                  Text(
                                    _mode == _HarnessMode.ask
                                        ? 'Agent is searching…'
                                        : 'Agent is working…',
                                    style: type.bodySmall?.copyWith(
                                      color: colors.muted,
                                    ),
                                  ),
                                ],
                              ],
                            ),
                          ),
                        ),
                      ],
                      if (_baselineBeforeProposal != null) ...[
                        const SizedBox(height: AppSpacing.grid),
                        DecoratedBox(
                          decoration: BoxDecoration(
                            color: scheme.surfaceContainerHighest,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(
                              horizontal: AppSpacing.grid * 2,
                              vertical: AppSpacing.grid,
                            ),
                            // Row + FilledButton under ListView can see
                            // w=Infinity on web (same freeze class as Jobs).
                            child: Wrap(
                              crossAxisAlignment: WrapCrossAlignment.center,
                              spacing: AppSpacing.grid,
                              runSpacing: AppSpacing.grid / 2,
                              children: [
                                Text(
                                  'Proposal is in the form below',
                                  style: type.bodySmall,
                                ),
                                TextButton(
                                  onPressed: _inputBusy
                                      ? null
                                      : _rejectProposal,
                                  child: const Text('Discard'),
                                ),
                                FilledButton.tonal(
                                  onPressed: _inputBusy
                                      ? null
                                      : _acceptProposal,
                                  child: const Text('Keep'),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                      const SizedBox(height: AppSpacing.grid),
                      Row(
                        children: [
                          Material(
                            color: _recording
                                ? scheme.error
                                : (_transcribing
                                      ? colors.muted
                                      : scheme.primary),
                            shape: const CircleBorder(),
                            child: InkWell(
                              customBorder: const CircleBorder(),
                              onTap: _micBusy ? null : _toggleMic,
                              child: SizedBox(
                                width: 48,
                                height: 48,
                                child: _transcribing
                                    ? Padding(
                                        padding: const EdgeInsets.all(14),
                                        child: CircularProgressIndicator(
                                          strokeWidth: 2,
                                          color: scheme.onPrimary,
                                        ),
                                      )
                                    : Icon(
                                        _recording ? Icons.stop : Icons.mic,
                                        color: Colors.white,
                                      ),
                              ),
                            ),
                          ),
                          const SizedBox(width: AppSpacing.grid * 1.5),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(_micHint, style: type.bodyMedium),
                                const SizedBox(height: 2),
                                if (_recording)
                                  const InterviewRecordingIndicator(
                                    active: true,
                                  )
                                else
                                  Text(
                                    _voiceInfo ?? 'Or type below.',
                                    style: type.bodySmall?.copyWith(
                                      color: colors.muted,
                                    ),
                                  ),
                              ],
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: AppSpacing.grid),
                      TextField(
                        controller: _instruction,
                        maxLines: 3,
                        readOnly: _recording || _transcribing,
                        decoration: InputDecoration(
                          labelText: _mode == _HarnessMode.ask
                              ? 'Question'
                              : 'Instruction',
                          hintText: _recording
                              ? 'Listening… tap stop when done'
                              : (_transcribing
                                    ? 'Transcribing…'
                                    : (_mode == _HarnessMode.ask
                                          ? 'Ask anything about this resume'
                                          : 'Describe the change you want')),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                      ),
                      const SizedBox(height: AppSpacing.grid),
                      OutlinedButton(
                        // Allow tap while recording — `_propose` stops +
                        // transcribes first (same pattern as deepen).
                        onPressed: (_proposing || _saving || _transcribing)
                            ? null
                            : _propose,
                        child: _proposing
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : Text(_ctaLabel),
                      ),
                      const SizedBox(height: AppSpacing.grid * 3),
                      if (_document != null)
                        ResumeDocumentForm(
                          key: ValueKey<int>(_formGen),
                          initialDocument: _document!,
                          enableDeepen: isMaster,
                          onState: (state) => _formState = state,
                          onDeepenExperience: isMaster
                              ? (i) => _deepen(section: 'experience', index: i)
                              : null,
                          onDeepenProject: isMaster
                              ? (i) => _deepen(section: 'projects', index: i)
                              : null,
                        ),
                      const SizedBox(height: AppSpacing.grid * 3),
                      FilledButton(
                        onPressed: _inputBusy ? null : _save,
                        child: _saving
                            ? SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: scheme.onPrimary,
                                ),
                              )
                            : const Text('Save'),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// One transcript message: You (right, tinted) / Agent (left, outlined).
class _ChatBubble extends StatelessWidget {
  const _ChatBubble({required this.entry});

  final _HistoryEntry entry;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final scheme = Theme.of(context).colorScheme;
    final isYou = entry.role == 'you';
    return Align(
      alignment: isYou ? Alignment.centerRight : Alignment.centerLeft,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 440),
        child: Column(
          crossAxisAlignment: isYou
              ? CrossAxisAlignment.end
              : CrossAxisAlignment.start,
          children: [
            Text(
              isYou ? 'You · ${entry.mode}' : 'Agent · ${entry.mode}',
              style: type.labelSmall?.copyWith(color: colors.muted),
            ),
            const SizedBox(height: 4),
            DecoratedBox(
              decoration: BoxDecoration(
                color: isYou ? scheme.surfaceContainerHighest : null,
                border: isYou ? null : Border.all(color: scheme.outlineVariant),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.grid * 1.5,
                  vertical: AppSpacing.grid,
                ),
                child: SelectableText(
                  entry.text,
                  style: type.bodyMedium?.copyWith(height: 1.4),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

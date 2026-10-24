import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../../onboarding/services/interview_audio.dart';
import '../../onboarding/state/onboarding_state.dart';
import '../../onboarding/widgets/interview_recording_indicator.dart';
import '../services/resume_service.dart';

/// Args for optional post-onboarding deepen (one role/project).
class ResumeDeepenArgs {
  const ResumeDeepenArgs({
    required this.resume,
    required this.section,
    required this.index,
  });

  final Map<String, dynamic> resume;

  /// `experience` or `projects`.
  final String section;
  final int index;
}

enum _DeepenPhase { choose, guided, journal, propose }

/// Dual-path deepen: guided novel Qs, or freeform journal dump.
/// Does not use `/onboarding/*` (no hard gate flip).
class ResumeDeepenScreen extends StatefulWidget {
  const ResumeDeepenScreen({super.key, required this.args});

  final ResumeDeepenArgs args;

  @override
  State<ResumeDeepenScreen> createState() => _ResumeDeepenScreenState();
}

class _ResumeDeepenScreenState extends State<ResumeDeepenScreen> {
  final _resumeService = ResumeService();
  final _transcriptCtrl = TextEditingController();
  final _audio = InterviewAudio();

  _DeepenPhase _phase = _DeepenPhase.choose;
  bool _loading = false;
  bool _submitting = false;
  bool _proposing = false;
  bool _recording = false;
  bool _transcribing = false;
  bool _micDenied = false;
  bool _audioUnsupported = false;
  String _seedBeforeRecord = '';
  String? _error;
  String? _info;

  String? _sessionId;
  String? _itemKind;
  String? _itemLabel;
  String? _question;
  int _qIndex = 0;
  int _qTotal = 0;
  List<String> _coverage = [];
  List<String> _hits = [];
  bool _itemComplete = false;
  bool _journalClarify = false;

  Map<String, dynamic>? _proposedResume;
  String? _proposeDetail;

  @override
  void initState() {
    super.initState();
    _audioUnsupported = !_audio.isSupported;
  }

  @override
  void dispose() {
    final sid = _sessionId;
    if (sid != null && sid.isNotEmpty) {
      _resumeService.clearDeepenSession(sid);
    }
    _audio.dispose();
    _transcriptCtrl.dispose();
    super.dispose();
  }

  Future<void> _chooseGuided() async {
    setState(() {
      _phase = _DeepenPhase.guided;
      _loading = true;
      _error = null;
    });
    try {
      final data = await _resumeService.deepenStart(
        resume: widget.args.resume,
        section: widget.args.section,
        index: widget.args.index,
        mode: 'guided',
      );
      if (!mounted) return;
      _applyState(data);
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = _dioMessage(e);
        _phase = _DeepenPhase.choose;
      });
    } on Object catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
        _phase = _DeepenPhase.choose;
      });
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _chooseJournal() {
    setState(() {
      _phase = _DeepenPhase.journal;
      _error = null;
      _info = null;
      _transcriptCtrl.clear();
      _journalClarify = false;
      _itemComplete = false;
      _proposedResume = null;
    });
  }

  void _backToChoose() {
    final sid = _sessionId;
    if (sid != null && sid.isNotEmpty) {
      _resumeService.clearDeepenSession(sid);
    }
    setState(() {
      _phase = _DeepenPhase.choose;
      _sessionId = null;
      _error = null;
      _info = null;
      _itemComplete = false;
      _journalClarify = false;
      _proposedResume = null;
      _proposeDetail = null;
      _transcriptCtrl.clear();
    });
  }

  void _applyState(Map<String, dynamic> data) {
    setState(() {
      _sessionId = data['session_id']?.toString();
      _itemKind = data['item_kind'] as String?;
      _itemLabel = data['item_label'] as String?;
      _question = data['question'] as String?;
      _qIndex = (data['question_index'] as num?)?.toInt() ?? 0;
      _qTotal = (data['question_total'] as num?)?.toInt() ?? 0;
      _coverage = (data['coverage'] as List? ?? []).map((e) => '$e').toList();
      _hits = (data['coverage_hits'] as List? ?? []).map((e) => '$e').toList();
      _itemComplete = data['item_complete'] == true;
      _transcriptCtrl.clear();
      _recording = false;
      _transcribing = false;
      _info = null;
    });
  }

  Future<void> _submitGuided({required bool forceDone}) async {
    if (_recording) await _stopAndTranscribe();
    if (_transcribing) return;
    final sid = _sessionId;
    if (sid == null) return;
    final text = _transcriptCtrl.text.trim();
    if (text.isEmpty && !forceDone) {
      setState(
        () => _error = 'Add a short answer (record or type) before continuing.',
      );
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final res = await _resumeService.deepenTurn(
        sessionId: sid,
        transcript: text,
        forceDone: forceDone,
      );
      if (!mounted) return;
      _applyState(res);
      if (res['item_complete'] == true) {
        setState(
          () => _info =
              'Done with this item — propose an enriched version when ready.',
        );
      }
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() => _error = _dioMessage(e));
    } on Object catch (e) {
      if (!mounted) return;
      setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  Future<void> _submitJournal() async {
    if (_recording) await _stopAndTranscribe();
    if (_transcribing) return;
    final text = _transcriptCtrl.text.trim();
    if (text.isEmpty) {
      setState(
        () => _error = 'Add a short update (record or type) — what happened, what you learnt…',
      );
      return;
    }

    setState(() {
      _submitting = true;
      _error = null;
      _info = null;
    });

    try {
      if (_journalClarify && _sessionId != null) {
        final res = await _resumeService.deepenTurn(
          sessionId: _sessionId!,
          transcript: text,
          forceDone: true,
        );
        if (!mounted) return;
        _applyState(res);
        setState(() {
          _journalClarify = false;
          _info = 'Ready — propose an enriched version when you like.';
        });
        return;
      }

      final res = await _resumeService.deepenJournal(
        resume: widget.args.resume,
        section: widget.args.section,
        index: widget.args.index,
        text: text,
      );
      if (!mounted) return;

      _sessionId = res['session_id']?.toString();
      _itemKind = res['item_kind'] as String?;
      _itemLabel = res['item_label'] as String?;

      if (res['needs_clarify'] == true) {
        setState(() {
          _journalClarify = true;
          _question = res['question'] as String?;
          _itemComplete = false;
          _transcriptCtrl.clear();
          _info =
              res['detail'] as String? ??
              'One quick clarify — then we can enrich this item.';
        });
        return;
      }

      final resume = res['resume'];
      if (resume is Map) {
        setState(() {
          _proposedResume = Map<String, dynamic>.from(resume);
          _proposeDetail = res['detail'] as String?;
          _itemComplete = true;
          _phase = _DeepenPhase.propose;
        });
        return;
      }

      setState(() {
        _itemComplete = true;
        _journalClarify = false;
        _info = 'Ready — propose an enriched version when you like.';
      });
    } on DioException catch (e) {
      if (!mounted) return;
      setState(() => _error = _dioMessage(e));
    } on Object catch (e) {
      if (!mounted) return;
      setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  Future<void> _propose() async {
    final sid = _sessionId;
    if (sid == null) return;
    setState(() {
      _proposing = true;
      _error = null;
    });
    try {
      final res = await _resumeService.deepenPropose(sessionId: sid);
      if (!mounted) return;
      final resume = res['resume'];
      if (resume is! Map) {
        throw StateError('Empty deepen proposal');
      }
      setState(() {
        _proposedResume = Map<String, dynamic>.from(resume);
        _proposeDetail = res['detail'] as String?;
        _proposing = false;
        _phase = _DeepenPhase.propose;
      });
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

  void _accept() {
    final doc = _proposedResume;
    if (doc == null) return;
    context.pop(doc);
  }

  void _discardProposal() {
    setState(() {
      _proposedResume = null;
      _proposeDetail = null;
      if (_phase == _DeepenPhase.propose) {
        _phase = _itemComplete
            ? (_sessionId != null ? _DeepenPhase.guided : _DeepenPhase.choose)
            : _DeepenPhase.choose;
        // Prefer returning to complete state of whatever mode we were in.
        if (_sessionId != null && _itemComplete) {
          // Stay on guided/journal complete UI via phase restore.
          final modeHint = _coverage.contains('Journal update')
              ? _DeepenPhase.journal
              : _DeepenPhase.guided;
          _phase = modeHint;
        }
      }
    });
  }

  Future<void> _toggleMic() async {
    if (_transcribing || _submitting || _proposing) return;

    if (_recording) {
      await _stopAndTranscribe();
      return;
    }

    if (_micDenied) {
      setState(
        () => _error =
            'Microphone permission was denied. Type your answer instead.',
      );
      return;
    }

    if (_audioUnsupported || !_audio.isSupported) {
      setState(() {
        _audioUnsupported = true;
        _error = 'Voice recording isn’t available in this browser. Type your answer below.';
      });
      return;
    }

    setState(() => _error = null);
    _seedBeforeRecord = _transcriptCtrl.text.trim();
    final result = await _audio.start();
    if (!mounted) return;

    switch (result) {
      case InterviewAudioStart.started:
        setState(() {
          _recording = true;
          _micDenied = false;
          _info = 'Recording… tap stop when you’re done.';
        });
      case InterviewAudioStart.denied:
        setState(() {
          _micDenied = true;
          _recording = false;
          _error =
              'Microphone permission was denied. Type your answer instead.';
        });
      case InterviewAudioStart.unsupported:
        setState(() {
          _audioUnsupported = true;
          _recording = false;
          _error = 'Voice recording isn’t available in this browser. Type your answer below.';
        });
      case InterviewAudioStart.failed:
        setState(() {
          _recording = false;
          _error = 'Couldn’t start the microphone. Check permissions, or type your answer.';
        });
    }
  }

  Future<void> _stopAndTranscribe() async {
    if (!_recording) return;
    setState(() {
      _recording = false;
      _transcribing = true;
      _info = 'Transcribing…';
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
        _error =
            'No audio was captured. Tap the mic to try again, or type instead.';
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
      _transcriptCtrl.value = TextEditingValue(
        text: merged,
        selection: TextSelection.collapsed(offset: merged.length),
      );
      setState(() {
        _info = 'Transcript ready — edit if needed, then continue.';
        _error = null;
      });
    } on DioException catch (e) {
      setState(() => _error = '${_dioMessage(e)} You can type instead.');
    } on Object catch (e) {
      setState(() => _error = 'Transcription failed ($e). Type instead.');
    } finally {
      if (mounted) setState(() => _transcribing = false);
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
    if (_transcribing) return 'Transcribing…';
    if (_recording) return 'Recording… tap to stop';
    if (_micDenied) return 'Mic blocked — type instead';
    if (_audioUnsupported) return 'Voice unavailable — type instead';
    return _phase == _DeepenPhase.journal
        ? 'Tap to record your update'
        : 'Tap to record your answer';
  }

  bool get _micBusy => _submitting || _transcribing || _proposing;

  bool get _isRole => _itemKind != 'project';

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;
    final colors = context.appColors;

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
                constraints: const BoxConstraints(maxWidth: 640),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Align(
                      alignment: Alignment.centerLeft,
                      child: TextButton(
                        onPressed: () {
                          if (_phase == _DeepenPhase.choose ||
                              _proposedResume != null) {
                            context.pop();
                          } else {
                            _backToChoose();
                          }
                        },
                        child: Text(
                          _phase == _DeepenPhase.choose
                              ? '← Back to editor'
                              : '← Choose how to deepen',
                        ),
                      ),
                    ),
                    const SizedBox(height: AppSpacing.grid),
                    if (_proposedResume != null)
                      _buildProposal(type, colors)
                    else if (_phase == _DeepenPhase.choose)
                      _buildChooser(type, colors, scheme)
                    else if (_loading)
                      const Padding(
                        padding: EdgeInsets.only(top: 48),
                        child: Center(child: CircularProgressIndicator()),
                      )
                    else if (_phase == _DeepenPhase.guided)
                      _buildGuided(type, colors, scheme)
                    else if (_phase == _DeepenPhase.journal)
                      _buildJournal(type, colors, scheme),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildChooser(TextTheme type, AppColors colors, ColorScheme scheme) {
    final isExp = widget.args.section == 'experience';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          isExp ? "Let's deepen this role" : "Let's deepen this project",
          style: type.headlineMedium,
        ),
        const SizedBox(height: AppSpacing.grid * 1.5),
        Text(
          'Choose how you want to add detail. Both end the same way: '
          'a proposed enrichment you can Accept into the editor, then Save.',
          style: type.bodyMedium?.copyWith(color: colors.muted, height: 1.45),
        ),
        if (_error != null) ...[
          const SizedBox(height: AppSpacing.grid * 2),
          Text(_error!, style: TextStyle(color: scheme.error)),
        ],
        const SizedBox(height: AppSpacing.grid * 3),
        _ChoiceCard(
          title: 'Deepen with questions',
          subtitle:
              'A few short, thoughtful prompts — voice or type. Fresh each time, '
              'grounded in what’s thin on this item.',
          cta: 'Start guided',
          onTap: _chooseGuided,
        ),
        const SizedBox(height: AppSpacing.grid * 2),
        _ChoiceCard(
          title: 'Add a daily/weekly update',
          subtitle:
              'Dump what happened today — no interview. We’ll weave it into '
              'the summary and bullets.',
          cta: 'Add update',
          onTap: _chooseJournal,
          outlined: true,
        ),
      ],
    );
  }

  Widget _buildGuided(TextTheme type, AppColors colors, ColorScheme scheme) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          _isRole ? 'Guided deepen — role' : 'Guided deepen — project',
          style: type.headlineMedium,
        ),
        const SizedBox(height: AppSpacing.grid),
        Text(
          'Short consultant questions specific to this item. Fuzzy memory '
          'and shared credit are fine.',
          style: type.bodyMedium?.copyWith(color: colors.muted, height: 1.45),
        ),
        const SizedBox(height: AppSpacing.grid * 2),
        if (_error != null && _sessionId == null) ...[
          Text(_error!, style: TextStyle(color: scheme.error)),
          const SizedBox(height: AppSpacing.grid * 2),
          OutlinedButton(
            onPressed: _chooseGuided,
            child: const Text('Try again'),
          ),
        ] else ...[
          if (_error != null) ...[
            Text(_error!, style: TextStyle(color: scheme.error)),
            const SizedBox(height: AppSpacing.grid),
          ],
          if (_info != null) ...[
            Text(
              _info!,
              style: type.bodySmall?.copyWith(color: scheme.primary),
            ),
            const SizedBox(height: AppSpacing.grid),
          ],
          Row(
            children: [
              Expanded(child: Text(_itemLabel ?? '', style: type.bodyLarge)),
              if (!_itemComplete && _qTotal > 0)
                Text(
                  'Part ${_qIndex + 1} of ~$_qTotal',
                  style: type.bodySmall?.copyWith(color: colors.muted),
                ),
            ],
          ),
          const SizedBox(height: AppSpacing.grid * 2),
          if (!_itemComplete) ...[
            Text(
              'UpdateApply',
              style: type.labelSmall?.copyWith(
                color: scheme.primary,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 6),
            Text(_question ?? '', style: type.bodyLarge?.copyWith(height: 1.4)),
            const SizedBox(height: AppSpacing.grid * 2.5),
            _micRow(type, colors, scheme),
            const SizedBox(height: AppSpacing.grid * 2),
            _answerField(
              hintRecording: 'Recording… transcript appears after you stop',
              hintIdle: 'Your answer appears here…',
            ),
            const SizedBox(height: AppSpacing.grid * 2),
            _coverageChips(scheme, colors),
            const SizedBox(height: AppSpacing.grid * 3),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: _micBusy
                        ? null
                        : () => _submitGuided(forceDone: true),
                    child: Text(
                      'Done with this ${_isRole ? 'role' : 'project'}',
                    ),
                  ),
                ),
                const SizedBox(width: AppSpacing.grid * 1.5),
                Expanded(
                  child: FilledButton(
                    onPressed: _micBusy
                        ? null
                        : () => _submitGuided(forceDone: false),
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
                                ? 'Finish'
                                : 'Next follow-up',
                          ),
                  ),
                ),
              ],
            ),
          ] else ...[
            _coverageChips(scheme, colors),
            const SizedBox(height: AppSpacing.grid * 3),
            FilledButton(
              onPressed: _proposing ? null : _propose,
              child: _proposing
                  ? SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: scheme.onPrimary,
                      ),
                    )
                  : const Text('Propose enriched item'),
            ),
            const SizedBox(height: AppSpacing.grid),
            TextButton(
              onPressed: () => context.pop(),
              child: const Text('Skip — keep stub in editor'),
            ),
          ],
        ],
      ],
    );
  }

  Widget _buildJournal(TextTheme type, AppColors colors, ColorScheme scheme) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('Add an update', style: type.headlineMedium),
        const SizedBox(height: AppSpacing.grid),
        Text(
          _journalClarify
              ? 'One clarify before we weave this in.'
              : 'No interview — dump what happened. Example: today at work my '
                    'manager let me operate the food production line, I learnt…',
          style: type.bodyMedium?.copyWith(color: colors.muted, height: 1.45),
        ),
        const SizedBox(height: AppSpacing.grid * 2),
        if (_error != null) ...[
          Text(_error!, style: TextStyle(color: scheme.error)),
          const SizedBox(height: AppSpacing.grid),
        ],
        if (_info != null) ...[
          Text(_info!, style: type.bodySmall?.copyWith(color: scheme.primary)),
          const SizedBox(height: AppSpacing.grid),
        ],
        if (_itemLabel != null && _itemLabel!.isNotEmpty) ...[
          Text(_itemLabel!, style: type.bodyLarge),
          const SizedBox(height: AppSpacing.grid * 2),
        ],
        if (_journalClarify) ...[
          Text(
            'UpdateApply',
            style: type.labelSmall?.copyWith(
              color: scheme.primary,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 6),
          Text(_question ?? '', style: type.bodyLarge?.copyWith(height: 1.4)),
          const SizedBox(height: AppSpacing.grid * 2.5),
        ],
        if (_itemComplete && !_journalClarify) ...[
          FilledButton(
            onPressed: _proposing ? null : _propose,
            child: _proposing
                ? SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: scheme.onPrimary,
                    ),
                  )
                : const Text('Propose enriched item'),
          ),
          const SizedBox(height: AppSpacing.grid),
          TextButton(
            onPressed: () => context.pop(),
            child: const Text('Skip — keep stub in editor'),
          ),
        ] else ...[
          _micRow(type, colors, scheme),
          const SizedBox(height: AppSpacing.grid * 2),
          _answerField(
            minLines: _journalClarify ? 3 : 5,
            maxLines: _journalClarify ? 6 : 10,
            hintRecording: 'Recording… transcript appears after you stop',
            hintIdle: _journalClarify
                ? 'Your clarify answer…'
                : 'What happened, what you learnt, what changed…',
          ),
          const SizedBox(height: AppSpacing.grid * 3),
          FilledButton(
            onPressed: _micBusy ? null : _submitJournal,
            child: _submitting
                ? SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: scheme.onPrimary,
                    ),
                  )
                : Text(_journalClarify ? 'Continue' : 'Add update'),
          ),
        ],
      ],
    );
  }

  Widget _buildProposal(TextTheme type, AppColors colors) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('Proposed enrichment', style: type.titleMedium),
        const SizedBox(height: AppSpacing.grid),
        if (_proposeDetail != null && _proposeDetail!.trim().isNotEmpty)
          Text(_proposeDetail!, style: type.bodyMedium?.copyWith(height: 1.4)),
        const SizedBox(height: AppSpacing.grid * 2),
        Text(
          'Accept merges into your editor form. Save there to persist '
          'and reindex for tailor.',
          style: type.bodySmall?.copyWith(color: colors.muted),
        ),
        const SizedBox(height: AppSpacing.grid * 2),
        Row(
          children: [
            Expanded(
              child: OutlinedButton(
                onPressed: _discardProposal,
                child: const Text('Discard'),
              ),
            ),
            const SizedBox(width: AppSpacing.grid),
            Expanded(
              child: FilledButton(
                onPressed: _accept,
                child: const Text('Accept into editor'),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _micRow(TextTheme type, AppColors colors, ColorScheme scheme) {
    return Row(
      children: [
        Material(
          color: _recording
              ? scheme.error
              : (_transcribing ? colors.muted : scheme.primary),
          shape: const CircleBorder(),
          child: InkWell(
            customBorder: const CircleBorder(),
            onTap: _micBusy ? null : _toggleMic,
            child: SizedBox(
              width: 56,
              height: 56,
              child: _transcribing
                  ? Padding(
                      padding: const EdgeInsets.all(16),
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
        const SizedBox(width: AppSpacing.grid * 2),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(_micHint, style: type.bodyLarge),
              const SizedBox(height: 4),
              if (_recording)
                const InterviewRecordingIndicator(active: true)
              else
                Text(
                  'Or type below.',
                  style: type.bodySmall?.copyWith(color: colors.muted),
                ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _answerField({
    required String hintRecording,
    required String hintIdle,
    int minLines = 3,
    int maxLines = 4,
  }) {
    final colors = context.appColors;
    final scheme = Theme.of(context).colorScheme;
    // Theme defaults use pillRadius (999) — fine for single-line, but multiline
    // text visually escapes a stadium outline. Match interview/tailor boxes.
    final radius = BorderRadius.circular(12);
    return TextField(
      controller: _transcriptCtrl,
      minLines: minLines,
      maxLines: maxLines,
      keyboardType: TextInputType.multiline,
      textAlignVertical: TextAlignVertical.top,
      readOnly: _recording || _transcribing,
      decoration: InputDecoration(
        hintText: _recording
            ? hintRecording
            : (_transcribing ? 'Transcribing…' : hintIdle),
        alignLabelWithHint: true,
        filled: true,
        fillColor: Colors.white,
        border: OutlineInputBorder(borderRadius: radius),
        enabledBorder: OutlineInputBorder(
          borderRadius: radius,
          borderSide: BorderSide(color: colors.inputBorder, width: 1.5),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: radius,
          borderSide: BorderSide(color: scheme.primary, width: 1.5),
        ),
        disabledBorder: OutlineInputBorder(
          borderRadius: radius,
          borderSide: BorderSide(color: colors.oauthBorder, width: 1.5),
        ),
      ),
    );
  }

  Widget _coverageChips(ColorScheme scheme, AppColors colors) {
    if (_coverage.isEmpty) return const SizedBox.shrink();
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: _coverage.map((c) {
        final hit = _hits.contains(c);
        return Chip(
          label: Text(c),
          backgroundColor: hit
              ? scheme.primary.withValues(alpha: 0.12)
              : scheme.surface,
          side: BorderSide(color: hit ? scheme.primary : colors.oauthBorder),
        );
      }).toList(),
    );
  }
}

class _ChoiceCard extends StatelessWidget {
  const _ChoiceCard({
    required this.title,
    required this.subtitle,
    required this.cta,
    required this.onTap,
    this.outlined = false,
  });

  final String title;
  final String subtitle;
  final String cta;
  final VoidCallback onTap;
  final bool outlined;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final scheme = Theme.of(context).colorScheme;

    return Material(
      color: scheme.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: colors.oauthBorder),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.grid * 2.5),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(title, style: type.titleMedium),
              const SizedBox(height: AppSpacing.grid),
              Text(
                subtitle,
                style: type.bodyMedium?.copyWith(
                  color: colors.muted,
                  height: 1.4,
                ),
              ),
              const SizedBox(height: AppSpacing.grid * 2),
              Align(
                alignment: Alignment.centerLeft,
                child: outlined
                    ? OutlinedButton(onPressed: onTap, child: Text(cta))
                    : FilledButton(onPressed: onTap, child: Text(cta)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

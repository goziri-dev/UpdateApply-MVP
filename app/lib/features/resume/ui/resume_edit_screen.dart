import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../../applications/services/applications_service.dart';
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
  final _formKey = GlobalKey<ResumeDocumentFormState>();
  final _instruction = TextEditingController();

  bool _loading = true;
  bool _saving = false;
  bool _proposing = false;
  String? _error;
  String? _banner;
  Map<String, dynamic>? _document;
  Map<String, dynamic>? _baselineBeforeProposal;
  String? _sessionId;
  String? _pendingOutcome;
  _HarnessMode _mode = _HarnessMode.edit;
  final List<_HistoryEntry> _history = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    final sid = _sessionId;
    if (sid != null && sid.isNotEmpty) {
      // Best-effort; do not block dispose.
      unawaited(_resumeService.clearEditSession(sid));
    }
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
        _document = doc;
        _loading = false;
      });
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _formKey.currentState?.applyDocument(doc);
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
        _document = saved;
        _banner = null;
        _baselineBeforeProposal = null;
        _saving = false;
      });
      _formKey.currentState?.applyDocument(saved);
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
    final form = _formKey.currentState;
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

  Future<void> _propose() async {
    final form = _formKey.currentState;
    if (form == null) return;
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
          _document = doc;
        } else {
          _baselineBeforeProposal = null;
        }
      });
      if (applied) {
        _formKey.currentState?.applyDocument(doc);
      }
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
      _document = baseline;
      _baselineBeforeProposal = null;
      _banner = 'Proposal discarded — form restored. Continue or try again.';
    });
    _formKey.currentState?.applyDocument(baseline);
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
    final form = _formKey.currentState;
    if (form == null) return;
    final current = form.toDocument();
    final result = await context.push<Map<String, dynamic>>(
      '/resume/deepen',
      extra: ResumeDeepenArgs(resume: current, section: section, index: index),
    );
    if (!mounted || result == null) return;
    setState(() {
      _document = result;
      _banner = 'Added to the form. Review, then save.';
      _error = null;
      _baselineBeforeProposal = null;
    });
    _formKey.currentState?.applyDocument(result);
  }

  String get _helperCopy => switch (_mode) {
    _HarnessMode.edit =>
      'Describe a change to your resume. We won’t invent details.',
    _HarnessMode.ask => 'Ask a question about your resume. Nothing changes until you switch to Edit.',
  };

  String get _ctaLabel => switch (_mode) {
    _HarnessMode.edit => 'Propose edits',
    _HarnessMode.ask => 'Ask',
  };

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
                            onPressed: _proposing || _saving
                                ? null
                                : _resetSession,
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
                              onSelected: _proposing || _saving
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
                            child: Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    'Proposal is in the form below',
                                    style: type.bodySmall,
                                  ),
                                ),
                                TextButton(
                                  onPressed: _proposing || _saving
                                      ? null
                                      : _rejectProposal,
                                  child: const Text('Discard'),
                                ),
                                FilledButton.tonal(
                                  onPressed: _proposing || _saving
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
                      TextField(
                        controller: _instruction,
                        maxLines: 3,
                        decoration: InputDecoration(
                          labelText: _mode == _HarnessMode.ask
                              ? 'Question'
                              : 'Instruction',
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                      ),
                      const SizedBox(height: AppSpacing.grid),
                      OutlinedButton(
                        onPressed: _proposing || _saving ? null : _propose,
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
                          key: _formKey,
                          initialDocument: _document!,
                          enableDeepen: isMaster,
                          onDeepenExperience: isMaster
                              ? (i) => _deepen(section: 'experience', index: i)
                              : null,
                          onDeepenProject: isMaster
                              ? (i) => _deepen(section: 'projects', index: i)
                              : null,
                        ),
                      const SizedBox(height: AppSpacing.grid * 3),
                      FilledButton(
                        onPressed: _saving || _proposing ? null : _save,
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

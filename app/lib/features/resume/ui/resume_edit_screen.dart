import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../../applications/services/applications_service.dart';
import '../services/resume_service.dart';
import '../widgets/resume_document_form.dart';
import 'resume_deepen_screen.dart';

enum ResumeEditTarget { master, application }

enum _HarnessMode { edit, advise, researchPropose }

extension on _HarnessMode {
  String get apiValue => switch (this) {
    _HarnessMode.edit => 'edit',
    _HarnessMode.advise => 'advise',
    _HarnessMode.researchPropose => 'research_propose',
  };

  String get label => switch (this) {
    _HarnessMode.edit => 'Edit',
    _HarnessMode.advise => 'Advise',
    _HarnessMode.researchPropose => 'Research',
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
      _banner = 'Edit session cleared — next message starts fresh.';
      _error = null;
    });
  }

  Future<void> _propose() async {
    final form = _formKey.currentState;
    if (form == null) return;
    final instruction = _instruction.text.trim();
    if (instruction.isEmpty) {
      setState(
        () => _error = _mode == _HarnessMode.advise
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
      final stub = result['stub'] == true;
      final applied = result['applied'] != false;
      final confidence = result['confidence'];
      if (!mounted) return;

      final historyYou = _HistoryEntry(
        role: 'you',
        text: instruction,
        mode: _mode.label,
      );
      final agentText = (detail != null && detail.trim().isNotEmpty)
          ? detail.trim()
          : (applied ? 'Proposed changes loaded.' : 'Advice ready.');
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
        if (applied) {
          _baselineBeforeProposal = current;
          _document = doc;
          final confBit = confidence is num
              ? ' Confidence: ${(confidence * 100).round()}%.'
              : '';
          _banner = stub
              ? (detail ?? 'Stub proposal — review before saving.')
              : '${detail ?? 'Proposed changes loaded — review fields, then Save to keep.'}$confBit';
        } else {
          _baselineBeforeProposal = null;
          _banner = detail ?? 'Advice ready — switch to Edit to apply changes.';
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
      _banner =
          'Proposal kept in the form — Save to persist, or continue editing.';
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
      _banner =
          'Deepen applied to the form — review, then Save to persist '
          'and reindex.';
      _error = null;
      _baselineBeforeProposal = null;
    });
    _formKey.currentState?.applyDocument(result);
  }

  String get _helperCopy => switch (_mode) {
    _HarnessMode.edit =>
      'Describe a change — e.g. “add Software Engineer at Acme, Jan 2024–present” '
          '(user-authored facts only) or “change the Acme start year to 2021.” '
          'Session memory lets you continue. We won’t invent metrics.',
    _HarnessMode.advise =>
      'Ask a coaching question — e.g. “Do I need a professional summary '
          'for US vs EU applications?” Advice won’t change the form until '
          'you switch to Edit.',
    _HarnessMode.researchPropose =>
      'Name something to verify before adding — e.g. “add Outlier as a '
          'role.” Needs TAVILY_API_KEY on the server; review confidence, '
          'then Save. Research mode stays alongside Edit + Advise.',
  };

  String get _ctaLabel => switch (_mode) {
    _HarnessMode.edit => 'Propose edits',
    _HarnessMode.advise => 'Ask',
    _HarnessMode.researchPropose => 'Research & propose',
  };

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final scheme = Theme.of(context).colorScheme;
    final isMaster = widget.target == ResumeEditTarget.master;
    final title = isMaster ? 'Edit master resume' : 'Edit tailored resume';
    final subtitle = isMaster
        ? 'Add or update roles anytime. Optional deepen (guided or journal) '
              'enriches one item — Save updates your master profile and index.'
        : 'Changes update this application’s tailored resume only.';

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
                      if (_baselineBeforeProposal != null) ...[
                        const SizedBox(height: AppSpacing.grid),
                        Row(
                          children: [
                            Expanded(
                              child: OutlinedButton(
                                onPressed: _proposing || _saving
                                    ? null
                                    : _rejectProposal,
                                child: const Text('Discard proposal'),
                              ),
                            ),
                            const SizedBox(width: AppSpacing.grid),
                            Expanded(
                              child: FilledButton.tonal(
                                onPressed: _proposing || _saving
                                    ? null
                                    : _acceptProposal,
                                child: const Text('Keep in form'),
                              ),
                            ),
                          ],
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
                      if (_history.isNotEmpty) ...[
                        const SizedBox(height: AppSpacing.grid * 2),
                        Text(
                          'This session',
                          style: type.labelLarge?.copyWith(color: colors.muted),
                        ),
                        const SizedBox(height: AppSpacing.grid),
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
                                    const SizedBox(height: AppSpacing.grid),
                                  Text(
                                    _history[i].role == 'you'
                                        ? 'You · ${_history[i].mode}'
                                        : 'Agent · ${_history[i].mode}',
                                    style: type.labelMedium?.copyWith(
                                      color: colors.muted,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    _history[i].text,
                                    style: type.bodySmall?.copyWith(
                                      height: 1.4,
                                    ),
                                  ),
                                ],
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
                          labelText: _mode == _HarnessMode.advise
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

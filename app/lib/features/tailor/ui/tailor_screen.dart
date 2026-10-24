import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../../resume/widgets/resume_preview.dart';
import '../services/tailor_service.dart';

class TailorScreen extends StatefulWidget {
  const TailorScreen({super.key});

  @override
  State<TailorScreen> createState() => _TailorScreenState();
}

class _TailorScreenState extends State<TailorScreen> {
  final _jdController = TextEditingController();
  final _roleController = TextEditingController();
  final _companyController = TextEditingController();
  final _service = TailorService();

  bool _busy = false;
  String? _error;
  String? _detail;
  bool _stub = false;
  Map<String, dynamic>? _resume;

  @override
  void dispose() {
    _jdController.dispose();
    _roleController.dispose();
    _companyController.dispose();
    super.dispose();
  }

  Future<void> _runTailor() async {
    final jd = _jdController.text.trim();
    if (jd.isEmpty) {
      setState(() => _error = 'Paste a job description first.');
      return;
    }

    setState(() {
      _busy = true;
      _error = null;
      _resume = null;
      _detail = null;
      _stub = false;
    });

    try {
      final data = await _service.tailor(
        jobDescription: jd,
        targetRole: _roleController.text,
        company: _companyController.text,
      );
      if (!mounted) return;

      final rawResume = data['resume'];
      final resume = rawResume is Map
          ? Map<String, dynamic>.from(rawResume)
          : null;
      if (resume == null || resume.isEmpty) {
        setState(() {
          _error =
              'Tailor response did not include a resume document. Try again.';
          _busy = false;
        });
        return;
      }

      setState(() {
        _resume = resume;
        _stub = data['stub'] == true;
        _detail = data['detail'] as String?;
        _busy = false;
      });
    } on DioException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = _dioMessage(error);
        _busy = false;
      });
    } on Object catch (error) {
      if (!mounted) return;
      setState(() {
        _error = '$error';
        _busy = false;
      });
    }
  }

  String _dioMessage(DioException error) {
    final detail = error.response?.data;
    if (detail is Map && detail['detail'] != null) {
      return detail['detail'].toString();
    }
    return error.message ?? 'Tailor request failed';
  }

  InputDecoration _boxDecoration(String label, {bool alignHint = false}) {
    final colors = context.appColors;
    final scheme = Theme.of(context).colorScheme;
    final radius = BorderRadius.circular(12);
    return InputDecoration(
      labelText: label,
      alignLabelWithHint: alignHint,
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
      errorBorder: OutlineInputBorder(
        borderRadius: radius,
        borderSide: BorderSide(color: scheme.error, width: 1.5),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final scheme = Theme.of(context).colorScheme;
    final wide = MediaQuery.sizeOf(context).width >= 900;

    final form = _TailorForm(
      jdController: _jdController,
      roleController: _roleController,
      companyController: _companyController,
      busy: _busy,
      error: _error,
      boxDecoration: _boxDecoration,
      onSubmit: _runTailor,
    );

    final result = _resume == null
        ? null
        : _TailorResult(resume: _resume!, stub: _stub, detail: _detail);

    return Scaffold(
      backgroundColor: scheme.surface,
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.grid * 3,
                vertical: AppSpacing.grid * 2,
              ),
              child: Row(
                children: [
                  TextButton(
                    onPressed: () => context.go('/'),
                    style: TextButton.styleFrom(
                      foregroundColor: scheme.onSurface,
                    ),
                    child: const Text('← Back'),
                  ),
                  const Spacer(),
                  Text(
                    'Tailor',
                    style: type.bodySmall?.copyWith(color: colors.muted),
                  ),
                ],
              ),
            ),
            Expanded(
              child: wide
                  ? Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: AppSpacing.grid * 3,
                      ),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(
                            flex: 5,
                            child: SingleChildScrollView(
                              padding: const EdgeInsets.only(
                                bottom: AppSpacing.grid * 4,
                                right: AppSpacing.grid * 3,
                              ),
                              child: ConstrainedBox(
                                constraints: const BoxConstraints(
                                  maxWidth: 520,
                                ),
                                child: form,
                              ),
                            ),
                          ),
                          Expanded(
                            flex: 4,
                            child: SingleChildScrollView(
                              padding: const EdgeInsets.only(
                                bottom: AppSpacing.grid * 4,
                              ),
                              child:
                                  result ??
                                  _PreviewPlaceholder(
                                    busy: _busy,
                                    muted: colors.muted,
                                  ),
                            ),
                          ),
                        ],
                      ),
                    )
                  : SingleChildScrollView(
                      padding: const EdgeInsets.fromLTRB(
                        AppSpacing.grid * 3,
                        0,
                        AppSpacing.grid * 3,
                        AppSpacing.grid * 4,
                      ),
                      child: Center(
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 560),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              form,
                              if (result != null) ...[
                                const SizedBox(height: AppSpacing.grid * 4),
                                result,
                              ] else if (_busy) ...[
                                const SizedBox(height: AppSpacing.grid * 4),
                                _PreviewPlaceholder(
                                  busy: true,
                                  muted: colors.muted,
                                ),
                              ],
                            ],
                          ),
                        ),
                      ),
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TailorForm extends StatelessWidget {
  const _TailorForm({
    required this.jdController,
    required this.roleController,
    required this.companyController,
    required this.busy,
    required this.error,
    required this.boxDecoration,
    required this.onSubmit,
  });

  final TextEditingController jdController;
  final TextEditingController roleController;
  final TextEditingController companyController;
  final bool busy;
  final String? error;
  final InputDecoration Function(String label, {bool alignHint}) boxDecoration;
  final VoidCallback onSubmit;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final scheme = Theme.of(context).colorScheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('Tailor resume', style: type.headlineMedium),
        const SizedBox(height: AppSpacing.grid * 1.5),
        Text(
          'Paste a job description. We match pieces of your remade profile '
          'and rewrite a resume aimed at that role.',
          style: type.bodyMedium?.copyWith(
            color: colors.muted,
            height: 1.45,
            fontWeight: FontWeight.w400,
          ),
        ),
        const SizedBox(height: AppSpacing.grid * 3),
        DecoratedBox(
          decoration: BoxDecoration(
            color: scheme.surfaceContainerHighest,
            borderRadius: BorderRadius.circular(16),
          ),
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.grid * 2.5),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                TextField(
                  controller: jdController,
                  enabled: !busy,
                  minLines: 8,
                  maxLines: 14,
                  decoration: boxDecoration('Job description', alignHint: true),
                ),
                const SizedBox(height: AppSpacing.grid * 2),
                TextField(
                  controller: roleController,
                  enabled: !busy,
                  decoration: boxDecoration('Target role (optional)'),
                ),
                const SizedBox(height: AppSpacing.grid * 2),
                TextField(
                  controller: companyController,
                  enabled: !busy,
                  decoration: boxDecoration('Company (optional)'),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.grid * 2.5),
        FilledButton(
          onPressed: busy ? null : onSubmit,
          child: busy
              ? const SizedBox(
                  width: 22,
                  height: 22,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: Colors.white,
                  ),
                )
              : const Text('Generate tailored resume'),
        ),
        if (busy) ...[
          const SizedBox(height: AppSpacing.grid * 2),
          Text(
            'Matching your profile and rewriting for this job…',
            textAlign: TextAlign.center,
            style: type.bodySmall?.copyWith(color: colors.muted, height: 1.4),
          ),
        ],
        if (error != null) ...[
          const SizedBox(height: AppSpacing.grid * 2),
          DecoratedBox(
            decoration: BoxDecoration(
              color: scheme.errorContainer,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.grid * 2,
                vertical: AppSpacing.grid * 1.5,
              ),
              child: Text(
                error!,
                style: type.bodyMedium?.copyWith(
                  color: scheme.error,
                  height: 1.4,
                ),
              ),
            ),
          ),
        ],
      ],
    );
  }
}

class _TailorResult extends StatelessWidget {
  const _TailorResult({
    required this.resume,
    required this.stub,
    required this.detail,
  });

  final Map<String, dynamic> resume;
  final bool stub;
  final String? detail;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final colors = context.appColors;
    final scheme = Theme.of(context).colorScheme;
    final meta = resume['meta'];
    final role = meta is Map ? (meta['target_role'] as String? ?? '') : '';
    final company = meta is Map ? (meta['company'] as String? ?? '') : '';
    final headline = [
      if (role.trim().isNotEmpty) role.trim(),
      if (company.trim().isNotEmpty) company.trim(),
    ].join(' · ');

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          headline.isNotEmpty ? headline : 'Tailored resume',
          style: type.titleMedium,
        ),
        if (detail != null) ...[
          const SizedBox(height: AppSpacing.grid),
          Text(
            detail!,
            style: type.bodySmall?.copyWith(
              color: colors.muted,
              height: 1.4,
              fontWeight: FontWeight.w400,
            ),
          ),
        ],
        if (stub) ...[
          const SizedBox(height: AppSpacing.grid * 1.5),
          DecoratedBox(
            decoration: BoxDecoration(
              color: scheme.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.grid * 2,
                vertical: AppSpacing.grid * 1.5,
              ),
              child: Text(
                'Stub response — this is your master resume mapped for '
                'preview, not a live JD rewrite. Configure OpenRouter on '
                'the server for real tailoring.',
                style: type.bodySmall?.copyWith(
                  color: colors.label,
                  height: 1.4,
                ),
              ),
            ),
          ),
        ],
        const SizedBox(height: AppSpacing.grid * 2),
        Center(
          child: ResumePreview(
            mode: ResumePreviewMode.full,
            resume: resume,
            viewTypePrefix: 'resume-tailor',
            maxWidth: 480,
          ),
        ),
        const SizedBox(height: AppSpacing.grid * 2.5),
        FilledButton(
          onPressed: () => downloadResumePdf(context, resume: resume),
          child: const Text('Download PDF'),
        ),
        const SizedBox(height: AppSpacing.grid),
        OutlinedButton(
          onPressed: () => showResumePreviewModal(context, resume: resume),
          child: const Text('Open larger preview'),
        ),
      ],
    );
  }
}

class _PreviewPlaceholder extends StatelessWidget {
  const _PreviewPlaceholder({required this.busy, required this.muted});

  final bool busy;
  final Color muted;

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;

    return DecoratedBox(
      decoration: BoxDecoration(
        color: scheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(16),
      ),
      child: AspectRatio(
        aspectRatio: kResumeLetterAspect,
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.grid * 3),
            child: busy
                ? Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const CircularProgressIndicator(strokeWidth: 2),
                      const SizedBox(height: AppSpacing.grid * 2),
                      Text(
                        'Building your tailored resume…',
                        textAlign: TextAlign.center,
                        style: type.bodySmall?.copyWith(
                          color: muted,
                          height: 1.4,
                        ),
                      ),
                    ],
                  )
                : Text(
                    'Your tailored resume will appear here after you generate.',
                    textAlign: TextAlign.center,
                    style: type.bodySmall?.copyWith(color: muted, height: 1.45),
                  ),
          ),
        ),
      ),
    );
  }
}

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../services/resume_download.dart';
import '../services/resume_service.dart';
import 'resume_html_frame.dart';

/// Letter aspect ratio (width / height) for ATS classic template.
const double kResumeLetterAspect = 8.5 / 11.0;

enum ResumePreviewMode {
  /// Full post-onboarding / modal preview.
  full,

  /// Shrunk dashboard card — tap handled by [onTap].
  mini,
}

/// Shared resume HTML preview (same server template as PDF export).
class ResumePreview extends StatefulWidget {
  const ResumePreview({
    super.key,
    this.mode = ResumePreviewMode.full,
    this.templateId = ResumeService.defaultTemplateId,
    this.resume,
    this.onTap,
    this.viewTypePrefix = 'resume-preview',
    this.maxWidth,
    this.showBorder = true,
  });

  final ResumePreviewMode mode;
  final String templateId;

  /// When set, POST /html with this document; otherwise GET master HTML.
  final Map<String, dynamic>? resume;

  /// Mini mode: open modal / navigate.
  final VoidCallback? onTap;

  final String viewTypePrefix;
  final double? maxWidth;
  final bool showBorder;

  @override
  State<ResumePreview> createState() => _ResumePreviewState();
}

class _ResumePreviewState extends State<ResumePreview> {
  final _service = ResumeService();
  late final String _viewType;

  String? _html;
  String? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _viewType =
        '${widget.viewTypePrefix}-${widget.mode.name}-${identityHashCode(this)}';
    _load();
  }

  @override
  void didUpdateWidget(covariant ResumePreview oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.templateId != widget.templateId ||
        oldWidget.resume != widget.resume) {
      _load();
    }
  }

  @override
  void dispose() {
    disposeResumeHtmlFrame(_viewType);
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final html = widget.resume != null
          ? await _service.fetchHtmlForResume(
              widget.resume!,
              templateId: widget.templateId,
            )
          : await _service.fetchMasterHtml(templateId: widget.templateId);
      if (!mounted) return;
      setState(() {
        _html = html;
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
        _error = e.toString();
        _loading = false;
      });
    }
  }

  String _dioMessage(DioException e) {
    final detail = e.response?.data;
    if (detail is Map && detail['detail'] != null) {
      return detail['detail'].toString();
    }
    return e.message ?? 'Could not load resume preview';
  }

  @override
  Widget build(BuildContext context) {
    final colors = context.appColors;
    final scheme = Theme.of(context).colorScheme;
    final isMini = widget.mode == ResumePreviewMode.mini;
    final maxW = widget.maxWidth ?? (isMini ? 168.0 : 560.0);

    Widget body;
    if (_loading) {
      body = const _StateBox(child: CircularProgressIndicator(strokeWidth: 2));
    } else if (_error != null) {
      body = _StateBox(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              isMini ? 'Preview unavailable' : _error!,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodySmall
                  ?.copyWith(color: colors.muted, height: 1.4),
            ),
            if (!isMini) ...[
              const SizedBox(height: AppSpacing.grid * 2),
              OutlinedButton(onPressed: _load, child: const Text('Try again')),
            ],
          ],
        ),
      );
    } else if (_html == null || _html!.isEmpty) {
      body = _StateBox(
        child: Text(
          'No resume yet. Finish onboarding first.',
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.bodySmall
              ?.copyWith(color: colors.muted),
        ),
      );
    } else {
      body = LayoutBuilder(
        builder: (context, constraints) {
          final width = constraints.maxWidth.isFinite
              ? constraints.maxWidth
              : maxW;
          final height = width / kResumeLetterAspect;
          return buildResumeHtmlFrame(
            viewType: _viewType,
            html: _html!,
            width: width,
            height: height,
            // Mini: parent InkWell owns taps; iframe must not eat events.
            interactive: !isMini,
          );
        },
      );
    }

    // Mini: IgnorePointer + overlay so HtmlElementView never steals taps
    // (Flutter web platform views sit above the Flutter hit-test tree).
    final previewBody = isMini && widget.onTap != null
        ? Stack(
            children: [
              IgnorePointer(child: body),
              Positioned.fill(
                child: Material(
                  color: Colors.transparent,
                  child: InkWell(
                    onTap: widget.onTap,
                    borderRadius: BorderRadius.circular(10),
                  ),
                ),
              ),
            ],
          )
        : body;

    final framed = DecoratedBox(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(isMini ? 10 : 12),
        border: widget.showBorder
            ? Border.all(color: colors.oauthBorder)
            : null,
        boxShadow: isMini
            ? [
                BoxShadow(
                  color: scheme.onSurface.withValues(alpha: 0.06),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ]
            : null,
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(isMini ? 10 : 12),
        child: previewBody,
      ),
    );

    return ConstrainedBox(
      constraints: BoxConstraints(maxWidth: maxW),
      child: framed,
    );
  }
}

class _StateBox extends StatelessWidget {
  const _StateBox({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: kResumeLetterAspect,
      child: ColoredBox(
        color: Theme.of(context).colorScheme.surfaceContainerHighest,
        child: Center(child: child),
      ),
    );
  }
}

/// Download master (or explicit) resume PDF via export API.
Future<void> downloadResumePdf(
  BuildContext context, {
  Map<String, dynamic>? resume,
  String templateId = ResumeService.defaultTemplateId,
  String? preferredName,
}) async {
  final messenger = ScaffoldMessenger.of(context);
  try {
    final bytes = await ResumeService().exportPdf(
      resume: resume,
      templateId: templateId,
    );
    var filename = (preferredName ?? '').trim();
    if (filename.isEmpty) {
      filename = 'resume.pdf';
      if (resume != null) {
        final basics = resume['basics'];
        if (basics is Map && basics['name'] is String) {
          final slug = (basics['name'] as String)
              .replaceAll(RegExp(r'[^A-Za-z0-9]+'), '_')
              .replaceAll(RegExp(r'^_+|_+$'), '');
          if (slug.isNotEmpty) filename = '$slug.pdf';
        }
      } else {
        try {
          final doc = await ResumeService().getDocument();
          final basics = doc['basics'];
          if (basics is Map && basics['name'] is String) {
            final slug = (basics['name'] as String)
                .replaceAll(RegExp(r'[^A-Za-z0-9]+'), '_')
                .replaceAll(RegExp(r'^_+|_+$'), '');
            if (slug.isNotEmpty) filename = '$slug.pdf';
          }
        } on Object {
          // keep resume.pdf
        }
      }
    }
    if (!filename.toLowerCase().endsWith('.pdf')) {
      filename = '$filename.pdf';
    }
    downloadPdfBytes(bytes, filename: filename);
    messenger.showSnackBar(const SnackBar(content: Text('Download started')));
  } on DioException catch (e) {
    final detail = e.response?.data;
    final message = detail is Map && detail['detail'] != null
        ? detail['detail'].toString()
        : (e.message ?? 'Download failed');
    messenger.showSnackBar(SnackBar(content: Text(message)));
  } on Object catch (e) {
    messenger.showSnackBar(SnackBar(content: Text('$e')));
  }
}

/// Larger preview + download in a modal (dashboard mini tap).
///
/// When [showEditMaster] is true (Home master mini), an Edit master resume
/// control sits under Download and opens `/resume/edit`.
Future<void> showResumePreviewModal(
  BuildContext context, {
  Map<String, dynamic>? resume,
  String templateId = ResumeService.defaultTemplateId,
  bool showEditMaster = false,
}) {
  return showDialog<void>(
    context: context,
    builder: (dialogContext) {
      final scheme = Theme.of(dialogContext).colorScheme;
      final type = Theme.of(dialogContext).textTheme;
      return Dialog(
        insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
        backgroundColor: scheme.surface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 640, maxHeight: 860),
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.grid * 2.5),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text('Your resume', style: type.titleMedium),
                    ),
                    IconButton(
                      tooltip: 'Close',
                      onPressed: () => Navigator.of(dialogContext).pop(),
                      icon: const Icon(Icons.close),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.grid),
                Expanded(
                  child: SingleChildScrollView(
                    child: Center(
                      child: ResumePreview(
                        mode: ResumePreviewMode.full,
                        resume: resume,
                        templateId: templateId,
                        viewTypePrefix: 'resume-modal',
                        maxWidth: 520,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: AppSpacing.grid * 2),
                FilledButton(
                  onPressed: () => downloadResumePdf(
                    dialogContext,
                    resume: resume,
                    templateId: templateId,
                  ),
                  child: const Text('Download PDF'),
                ),
                if (showEditMaster) ...[
                  const SizedBox(height: AppSpacing.grid),
                  OutlinedButton(
                    onPressed: () {
                      Navigator.of(dialogContext).pop();
                      context.push('/resume/edit');
                    },
                    child: const Text('Edit master resume'),
                  ),
                ],
              ],
            ),
          ),
        ),
      );
    },
  );
}

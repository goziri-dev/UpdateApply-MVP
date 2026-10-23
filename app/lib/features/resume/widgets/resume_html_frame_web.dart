import 'dart:ui_web' as ui_web;

import 'package:flutter/widgets.dart';
import 'package:web/web.dart' as web;

/// CSS px for 8.5in at 96dpi — matches letter template layout width.
const double _kLetterCssWidth = 816;

/// Letter height for [_kLetterCssWidth] (11/8.5).
const double _kLetterCssHeight = _kLetterCssWidth * 11 / 8.5;

final Map<String, web.HTMLIFrameElement> _iframes = {};

Widget buildResumeHtmlFrame({
  required String viewType,
  required String html,
  required double width,
  required double height,
  bool interactive = true,
}) {
  final scale = width / _kLetterCssWidth;

  void configure(web.HTMLIFrameElement iframe) {
    iframe
      ..style.border = 'none'
      ..style.width = '${_kLetterCssWidth}px'
      ..style.height = '${_kLetterCssHeight}px'
      ..style.transform = 'scale($scale)'
      ..style.transformOrigin = 'top left'
      ..style.backgroundColor = '#ffffff'
      // Platform views sit above Flutter hit-testing; disable when the parent
      // owns taps (e.g. mini preview → modal).
      ..style.pointerEvents = interactive ? 'auto' : 'none'
      ..setAttribute('srcdoc', html);
  }

  // Factory may already exist for this viewType (hot reload / rebuild).
  if (!_iframes.containsKey(viewType)) {
    ui_web.platformViewRegistry.registerViewFactory(viewType, (int viewId) {
      final iframe = web.HTMLIFrameElement();
      configure(iframe);
      _iframes[viewType] = iframe;
      return iframe;
    });
  } else {
    configure(_iframes[viewType]!);
  }

  return SizedBox(
    width: width,
    height: height,
    child: HtmlElementView(viewType: viewType),
  );
}

void disposeResumeHtmlFrame(String viewType) {
  _iframes.remove(viewType);
}

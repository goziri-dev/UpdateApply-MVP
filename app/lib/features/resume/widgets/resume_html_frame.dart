import 'resume_html_frame_stub.dart'
    if (dart.library.js_interop) 'resume_html_frame_web.dart'
    as impl;

import 'package:flutter/widgets.dart';

export 'resume_html_frame_stub.dart'
    if (dart.library.js_interop) 'resume_html_frame_web.dart'
    show clearAllResumeHtmlFrames, disposeResumeHtmlFrame;

Widget buildResumeHtmlFrame({
  required String viewType,
  required String html,
  required double width,
  required double height,
  bool interactive = true,
}) {
  return impl.buildResumeHtmlFrame(
    viewType: viewType,
    html: html,
    width: width,
    height: height,
    interactive: interactive,
  );
}

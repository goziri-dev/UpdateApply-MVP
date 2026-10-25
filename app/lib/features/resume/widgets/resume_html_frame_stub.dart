import 'package:flutter/material.dart';

/// Non-web placeholder — preview is web-first.
Widget buildResumeHtmlFrame({
  required String viewType,
  required String html,
  required double width,
  required double height,
  bool interactive = true,
}) {
  return SizedBox(
    width: width,
    height: height,
    child: const ColoredBox(
      color: Color(0xFFF5F5F5),
      child: Center(
        child: Text(
          'Resume preview is available on web.',
          style: TextStyle(color: Color(0xFF6B6B6B), fontSize: 13),
        ),
      ),
    ),
  );
}

void disposeResumeHtmlFrame(String viewType) {}

void clearAllResumeHtmlFrames() {}

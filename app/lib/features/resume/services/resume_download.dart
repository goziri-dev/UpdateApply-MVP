import 'dart:typed_data';

import 'resume_download_stub.dart'
    if (dart.library.js_interop) 'resume_download_web.dart'
    as impl;

/// Trigger a browser download of PDF bytes (web). No-op / throw on stub.
void downloadPdfBytes(Uint8List bytes, {required String filename}) {
  impl.downloadPdfBytes(bytes, filename: filename);
}

import 'dart:typed_data';

void downloadPdfBytes(Uint8List bytes, {required String filename}) {
  throw UnsupportedError(
    'PDF download is only supported on Flutter web in this build.',
  );
}

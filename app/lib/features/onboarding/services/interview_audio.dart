import 'dart:typed_data';

import 'interview_audio_stub.dart'
    if (dart.library.js_interop) 'interview_audio_web.dart'
    as impl;

/// Outcome of starting browser mic capture.
enum InterviewAudioStart { started, unsupported, denied, failed }

/// Recorded clip ready to upload for Whisper transcription.
class InterviewAudioClip {
  const InterviewAudioClip({
    required this.bytes,
    required this.filename,
    required this.mimeType,
  });

  final Uint8List bytes;
  final String filename;
  final String mimeType;
}

/// Platform mic capture for the onboarding interview (MediaRecorder on web).
///
/// Does not run live STT — the UI shows a recording state, then uploads the
/// clip for server-side Whisper transcription.
abstract class InterviewAudio {
  factory InterviewAudio() => impl.createInterviewAudio();

  bool get isSupported;
  bool get isRecording;

  Future<InterviewAudioStart> start();

  /// Stop capture and return the full clip, or null if nothing was recorded.
  Future<InterviewAudioClip?> stop();

  void dispose();
}

import 'interview_speech_stub.dart'
    if (dart.library.js_interop) 'interview_speech_web.dart'
    as impl;

/// Outcome of starting browser speech recognition.
enum InterviewSpeechStart { started, unsupported, denied, failed }

/// Live STT updates for the interview transcript field.
class InterviewSpeechUpdate {
  const InterviewSpeechUpdate({
    required this.transcript,
    required this.isFinal,
  });

  final String transcript;
  final bool isFinal;
}

/// Platform speech capture for the onboarding interview (web Speech API first).
abstract class InterviewSpeech {
  factory InterviewSpeech() => impl.createInterviewSpeech();

  bool get isSupported;
  bool get isListening;

  /// Start listening. [onUpdate] receives interim/final transcript text.
  /// [onEnded] fires when the session stops (user stop, error, or browser end).
  /// [seedTranscript] keeps any already-typed text when dictation begins.
  Future<InterviewSpeechStart> start({
    required void Function(InterviewSpeechUpdate update) onUpdate,
    required void Function({String? error}) onEnded,
    String lang = 'en-US',
    String seedTranscript = '',
  });

  Future<void> stop();
  void dispose();
}

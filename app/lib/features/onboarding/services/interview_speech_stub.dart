import 'interview_speech.dart';

InterviewSpeech createInterviewSpeech() => _UnsupportedInterviewSpeech();

class _UnsupportedInterviewSpeech implements InterviewSpeech {
  @override
  bool get isSupported => false;

  @override
  bool get isListening => false;

  @override
  Future<InterviewSpeechStart> start({
    required void Function(InterviewSpeechUpdate update) onUpdate,
    required void Function({String? error}) onEnded,
    String lang = 'en-US',
    String seedTranscript = '',
  }) async {
    return InterviewSpeechStart.unsupported;
  }

  @override
  Future<void> stop() async {}

  @override
  void dispose() {}
}

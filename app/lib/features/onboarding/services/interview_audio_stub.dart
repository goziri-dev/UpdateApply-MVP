import 'interview_audio.dart';

InterviewAudio createInterviewAudio() => _UnsupportedInterviewAudio();

class _UnsupportedInterviewAudio implements InterviewAudio {
  @override
  bool get isSupported => false;

  @override
  bool get isRecording => false;

  @override
  Future<InterviewAudioStart> start() async {
    return InterviewAudioStart.unsupported;
  }

  @override
  Future<InterviewAudioClip?> stop() async => null;

  @override
  void dispose() {}
}

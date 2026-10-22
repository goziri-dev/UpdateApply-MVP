import 'dart:async';
import 'dart:js_interop';
import 'dart:typed_data';

import 'package:web/web.dart';

import 'interview_audio.dart';

InterviewAudio createInterviewAudio() => WebInterviewAudio();

/// Browser [MediaRecorder] capture for interview answers (no live STT).
class WebInterviewAudio implements InterviewAudio {
  MediaStream? _stream;
  MediaRecorder? _recorder;
  final List<Blob> _chunks = [];
  bool _recording = false;
  Completer<InterviewAudioClip?>? _stopCompleter;
  String _mimeType = 'audio/webm';

  @override
  bool get isSupported {
    try {
      // Touch MediaDevices + MediaRecorder so unsupported engines fail closed.
      window.navigator.mediaDevices;
      MediaRecorder.isTypeSupported('audio/webm');
      return true;
    } on Object {
      return false;
    }
  }

  @override
  bool get isRecording => _recording;

  @override
  Future<InterviewAudioStart> start() async {
    if (!isSupported) return InterviewAudioStart.unsupported;
    if (_recording) return InterviewAudioStart.started;

    try {
      final stream = await window.navigator.mediaDevices
          .getUserMedia(
            MediaStreamConstraints(audio: true.toJS, video: false.toJS),
          )
          .toDart;
      final mimeType = _pickMimeType();
      final recorder = mimeType != null
          ? MediaRecorder(stream, MediaRecorderOptions(mimeType: mimeType))
          : MediaRecorder(stream);

      _chunks.clear();
      _stream = stream;
      _recorder = recorder;
      _mimeType = recorder.mimeType.isNotEmpty
          ? recorder.mimeType
          : (mimeType ?? 'audio/webm');
      _stopCompleter = null;

      recorder.ondataavailable = _onDataAvailable.toJS;
      recorder.onstop = _onStop.toJS;
      recorder.onerror = _onError.toJS;

      recorder.start();
      _recording = true;
      return InterviewAudioStart.started;
    } on Object catch (e) {
      _cleanupStream();
      if (e.isA<DOMException>()) {
        final name = (e as DOMException).name.toLowerCase();
        if (name.contains('notallowed') || name.contains('security')) {
          return InterviewAudioStart.denied;
        }
      }
      return InterviewAudioStart.failed;
    }
  }

  @override
  Future<InterviewAudioClip?> stop() async {
    final recorder = _recorder;
    if (!_recording || recorder == null) {
      return null;
    }
    if (_stopCompleter != null) {
      return _stopCompleter!.future;
    }
    final completer = Completer<InterviewAudioClip?>();
    _stopCompleter = completer;
    try {
      if (recorder.state == 'recording' || recorder.state == 'paused') {
        recorder.stop();
      } else {
        _recording = false;
        _finishStop(null);
      }
    } on Object {
      _recording = false;
      _finishStop(null);
    }
    return completer.future;
  }

  @override
  void dispose() {
    final recorder = _recorder;
    _recorder = null;
    if (recorder != null) {
      try {
        if (recorder.state == 'recording' || recorder.state == 'paused') {
          recorder.stop();
        }
      } on Object {
        // Ignore dispose races.
      }
    }
    _cleanupStream();
    _chunks.clear();
    _recording = false;
    if (_stopCompleter != null && !_stopCompleter!.isCompleted) {
      _stopCompleter!.complete(null);
    }
    _stopCompleter = null;
  }

  void _onDataAvailable(Event event) {
    final blobEvent = event as BlobEvent;
    final data = blobEvent.data;
    if (data.size > 0) {
      _chunks.add(data);
    }
  }

  void _onError(Event event) {
    _recording = false;
    _cleanupStream();
    _finishStop(null);
  }

  void _onStop(Event event) {
    unawaited(_finalizeClip());
  }

  Future<void> _finalizeClip() async {
    _recording = false;
    _cleanupStream();
    try {
      if (_chunks.isEmpty) {
        _finishStop(null);
        return;
      }
      final blob = Blob(_chunks.toJS, BlobPropertyBag(type: _mimeType));
      _chunks.clear();
      final buffer = await blob.arrayBuffer().toDart;
      final bytes = Uint8List.view(buffer.toDart);
      if (bytes.isEmpty) {
        _finishStop(null);
        return;
      }
      final filename = _filenameForMime(_mimeType);
      _finishStop(
        InterviewAudioClip(
          bytes: bytes,
          filename: filename,
          mimeType: _mimeType.split(';').first,
        ),
      );
    } on Object {
      _finishStop(null);
    }
  }

  void _finishStop(InterviewAudioClip? clip) {
    final completer = _stopCompleter;
    _stopCompleter = null;
    _recorder = null;
    if (completer != null && !completer.isCompleted) {
      completer.complete(clip);
    }
  }

  void _cleanupStream() {
    final stream = _stream;
    _stream = null;
    if (stream == null) return;
    final tracks = stream.getTracks().toDart;
    for (final track in tracks) {
      track.stop();
    }
  }

  static String? _pickMimeType() {
    const candidates = <String>[
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/mp4',
      'audio/ogg;codecs=opus',
      'audio/ogg',
    ];
    for (final type in candidates) {
      if (MediaRecorder.isTypeSupported(type)) return type;
    }
    return null;
  }

  static String _filenameForMime(String mime) {
    final base = mime.split(';').first.toLowerCase();
    if (base.contains('mp4') || base.contains('m4a')) return 'recording.m4a';
    if (base.contains('ogg')) return 'recording.ogg';
    if (base.contains('wav')) return 'recording.wav';
    return 'recording.webm';
  }
}

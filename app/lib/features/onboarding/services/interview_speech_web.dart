import 'dart:js_interop';
import 'dart:js_interop_unsafe';

import 'package:web/web.dart';

import 'interview_speech.dart';

InterviewSpeech createInterviewSpeech() => WebInterviewSpeech();

/// Browser Web Speech API (`SpeechRecognition` / `webkitSpeechRecognition`).
///
/// Chrome/Edge use a cloud recognizer and require a secure context (HTTPS or
/// localhost). Firefox support is limited — typed fallback remains available.
class WebInterviewSpeech implements InterviewSpeech {
  SpeechRecognition? _recognition;
  bool _wantListening = false;
  bool _listening = false;

  /// Finalized text kept across Chrome pause/restart cycles + optional seed.
  String _committed = '';

  /// Finals from the current recognition bout (results reset on restart).
  String _boutFinal = '';
  String _interim = '';
  String? _pendingError;

  void Function(InterviewSpeechUpdate update)? _onUpdate;
  void Function({String? error})? _onEnded;

  @override
  bool get isSupported => _speechRecognitionConstructor != null;

  @override
  bool get isListening => _listening;

  @override
  Future<InterviewSpeechStart> start({
    required void Function(InterviewSpeechUpdate update) onUpdate,
    required void Function({String? error}) onEnded,
    String lang = 'en-US',
    String seedTranscript = '',
  }) async {
    if (!isSupported) return InterviewSpeechStart.unsupported;
    if (_listening) return InterviewSpeechStart.started;

    _onUpdate = onUpdate;
    _onEnded = onEnded;
    _committed = seedTranscript.trim();
    _boutFinal = '';
    _interim = '';
    _pendingError = null;
    _wantListening = true;

    final recognition = _createRecognition();
    if (recognition == null) return InterviewSpeechStart.unsupported;

    recognition.lang = lang;
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onresult = _handleResult.toJS;
    recognition.onerror = _handleError.toJS;
    recognition.onend = _handleEnd.toJS;

    _recognition = recognition;
    try {
      recognition.start();
      _listening = true;
      return InterviewSpeechStart.started;
    } on Object {
      _wantListening = false;
      _listening = false;
      _recognition = null;
      return InterviewSpeechStart.failed;
    }
  }

  @override
  Future<void> stop() async {
    _wantListening = false;
    final recognition = _recognition;
    if (recognition == null) {
      _listening = false;
      return;
    }
    try {
      recognition.stop();
    } on Object {
      // Already stopped.
    }
  }

  @override
  void dispose() {
    _wantListening = false;
    _onUpdate = null;
    _onEnded = null;
    final recognition = _recognition;
    _recognition = null;
    if (recognition != null) {
      try {
        recognition.abort();
      } on Object {
        // Ignore dispose races.
      }
    }
    _listening = false;
  }

  void _emit() {
    final transcript = [
      if (_committed.isNotEmpty) _committed,
      if (_boutFinal.isNotEmpty) _boutFinal,
      if (_interim.isNotEmpty) _interim,
    ].join(' ').trim();
    _onUpdate?.call(
      InterviewSpeechUpdate(transcript: transcript, isFinal: _interim.isEmpty),
    );
  }

  void _foldBoutIntoCommitted() {
    if (_boutFinal.isEmpty) {
      _interim = '';
      return;
    }
    _committed = [
      if (_committed.isNotEmpty) _committed,
      _boutFinal,
    ].join(' ').trim();
    _boutFinal = '';
    _interim = '';
  }

  void _handleResult(Event event) {
    final speechEvent = event as SpeechRecognitionEvent;
    final results = speechEvent.results;
    final finals = StringBuffer();
    var interim = '';

    for (var i = 0; i < results.length; i++) {
      final result = results.item(i);
      if (result.length == 0) continue;
      final text = result.item(0).transcript.trim();
      if (text.isEmpty) continue;
      if (result.isFinal) {
        if (finals.isNotEmpty) finals.write(' ');
        finals.write(text);
      } else {
        interim = interim.isEmpty ? text : '$interim $text';
      }
    }

    _boutFinal = finals.toString().trim();
    _interim = interim;
    _emit();
  }

  void _handleError(Event event) {
    final code = (event as SpeechRecognitionErrorEvent).error;
    if (code == 'not-allowed' || code == 'service-not-allowed') {
      _wantListening = false;
      _pendingError = code;
      return;
    }
    if (code == 'aborted' || code == 'no-speech') {
      return;
    }
    _pendingError = code;
  }

  void _handleEnd(Event event) {
    _foldBoutIntoCommitted();
    _emit();

    if (_wantListening && _pendingError == null) {
      // Chrome often ends after a pause; restart while the user still wants mic.
      try {
        _recognition?.start();
        return;
      } on Object {
        _wantListening = false;
      }
    }

    _listening = false;
    final err = _pendingError;
    _pendingError = null;
    _onEnded?.call(error: err);
  }

  SpeechRecognition? _createRecognition() {
    final ctor = _speechRecognitionConstructor;
    if (ctor == null) return null;
    return ctor.callAsConstructor<SpeechRecognition>();
  }
}

JSFunction? get _speechRecognitionConstructor {
  final speech = globalContext.getProperty('SpeechRecognition'.toJS);
  if (speech != null && speech.isA<JSFunction>()) {
    return speech as JSFunction;
  }
  final webkit = globalContext.getProperty('webkitSpeechRecognition'.toJS);
  if (webkit != null && webkit.isA<JSFunction>()) {
    return webkit as JSFunction;
  }
  return null;
}

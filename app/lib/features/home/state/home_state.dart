import 'package:scoped_deps/scoped_deps.dart';
import 'package:signals/signals.dart';

final homeMessageRef = create(
  () => signal('UpdateApply — paste a JD, get a tailored resume.'),
);

// See auth_state.dart — hot reload safe fallback when zone refs are stale.
Signal<String>? _homeMessageFallback;

Signal<String> get homeMessage => read(
  homeMessageRef,
  orElse: () => _homeMessageFallback ??= signal(
    'UpdateApply — paste a JD, get a tailored resume.',
  ),
);

void setHomeMessage(String value) => homeMessage.value = value;

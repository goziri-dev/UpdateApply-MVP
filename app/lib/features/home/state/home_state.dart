import 'package:scoped_deps/scoped_deps.dart';
import 'package:signals/signals.dart';

final homeMessageRef = create(
  () => signal('UpdateApply — paste a JD, get a tailored resume.'),
);

Signal<String> get homeMessage => read(homeMessageRef);

void setHomeMessage(String value) => homeMessage.value = value;

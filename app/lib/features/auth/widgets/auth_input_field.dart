import 'package:flutter/material.dart';

import '../../../core/theme/app_theme.dart';

enum AuthInputKind { email, password }

class AuthInputField extends StatelessWidget {
  const AuthInputField({
    super.key,
    required this.kind,
    required this.controller,
    this.onSubmitted,
    this.autofillHints,
  });

  final AuthInputKind kind;
  final TextEditingController controller;
  final ValueChanged<String>? onSubmitted;
  final Iterable<String>? autofillHints;

  String get _label => switch (kind) {
    AuthInputKind.email => 'Email',
    AuthInputKind.password => 'Password',
  };

  String? get _hint => switch (kind) {
    AuthInputKind.email => 'you@example.com',
    AuthInputKind.password => null,
  };

  TextInputType get _keyboardType => switch (kind) {
    AuthInputKind.email => TextInputType.emailAddress,
    AuthInputKind.password => TextInputType.visiblePassword,
  };

  @override
  Widget build(BuildContext context) {
    final type = Theme.of(context).textTheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 2, bottom: AppSpacing.grid),
          child: Text(_label, style: type.bodySmall),
        ),
        TextField(
          controller: controller,
          obscureText: kind == AuthInputKind.password,
          keyboardType: _keyboardType,
          textInputAction: kind == AuthInputKind.email
              ? TextInputAction.next
              : TextInputAction.done,
          textAlign: TextAlign.center,
          autofillHints: autofillHints,
          onSubmitted: onSubmitted,
          style: type.bodyLarge,
          decoration: InputDecoration(hintText: _hint),
        ),
      ],
    );
  }
}

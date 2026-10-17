import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_theme.dart';
import '../state/auth_state.dart';
import '../widgets/auth_error_banner.dart';
import '../widgets/auth_header.dart';
import '../widgets/auth_input_field.dart';
import '../widgets/auth_legal_footer.dart';
import '../widgets/auth_mode_switch.dart';
import '../widgets/auth_oauth_stack.dart';
import '../widgets/auth_primary_button.dart';
import '../widgets/auth_shell.dart';

/// Production auth UI — matches `prototypes/auth/` (Refero-style + forest u+).
class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  AuthScreenMode _mode = AuthScreenMode.signIn;
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  void _setMode(AuthScreenMode mode) {
    if (_mode == mode) return;
    clearAuthFeedback();
    setState(() => _mode = mode);
  }

  void _toggleSignInUp() {
    clearAuthFeedback();
    setState(() {
      _mode = _mode == AuthScreenMode.signIn
          ? AuthScreenMode.signUp
          : AuthScreenMode.signIn;
    });
  }

  Future<void> _submitEmailFlow() async {
    final email = _emailController.text.trim();
    if (email.isEmpty) {
      setAuthError('Enter your email address.');
      return;
    }

    switch (_mode) {
      case AuthScreenMode.signIn:
        final password = _passwordController.text;
        if (password.isEmpty) {
          setAuthError('Enter your password.');
          return;
        }
        await signInWithEmail(email: email, password: password);
      case AuthScreenMode.signUp:
        final password = _passwordController.text;
        if (password.length < 6) {
          setAuthError('Password must be at least 6 characters.');
          return;
        }
        await signUpWithEmail(email: email, password: password);
      case AuthScreenMode.resetPassword:
        await sendPasswordReset(email: email);
    }
  }

  @override
  Widget build(BuildContext context) {
    final colors = context.appColors;
    final showPassword = _mode != AuthScreenMode.resetPassword;
    final showOAuth = _mode != AuthScreenMode.resetPassword;
    final showResetLink = _mode == AuthScreenMode.signIn;

    final (primaryIdle, primaryLoading, busyTarget) = switch (_mode) {
      AuthScreenMode.signIn => ('Sign in', 'Signing in…', AuthBusyTarget.email),
      AuthScreenMode.signUp => (
        'Sign up',
        'Creating account…',
        AuthBusyTarget.email,
      ),
      AuthScreenMode.resetPassword => (
        'Send reset link',
        'Sending…',
        AuthBusyTarget.reset,
      ),
    };

    return AuthShell(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          AuthHeader(mode: _mode),
          const AuthFeedbackBanner(),
          AutofillGroup(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                AuthInputField(
                  kind: AuthInputKind.email,
                  controller: _emailController,
                  autofillHints: const [AutofillHints.email],
                  onSubmitted: showPassword
                      ? (_) => FocusScope.of(context).nextFocus()
                      : (_) => _submitEmailFlow(),
                ),
                if (showPassword) ...[
                  const SizedBox(height: AppSpacing.grid * 2),
                  AuthInputField(
                    kind: AuthInputKind.password,
                    controller: _passwordController,
                    autofillHints: _mode == AuthScreenMode.signUp
                        ? const [AutofillHints.newPassword]
                        : const [AutofillHints.password],
                    onSubmitted: (_) => _submitEmailFlow(),
                  ),
                  if (showResetLink)
                    Align(
                      alignment: Alignment.centerRight,
                      child: TextButton(
                        onPressed: isAuthBusy
                            ? null
                            : () => _setMode(AuthScreenMode.resetPassword),
                        style: TextButton.styleFrom(
                          foregroundColor: colors.link,
                          padding: const EdgeInsets.only(top: AppSpacing.grid),
                          minimumSize: Size.zero,
                          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        ),
                        child: const Text('Reset Password?'),
                      ),
                    ),
                ],
                AuthPrimaryButton(
                  idleLabel: primaryIdle,
                  loadingLabel: primaryLoading,
                  busyTarget: busyTarget,
                  onPressed: _submitEmailFlow,
                ),
              ],
            ),
          ),
          AuthModeSwitch(mode: _mode, onToggle: _toggleSignInUp),
          if (showOAuth) const AuthOAuthStack(),
          const AuthLegalFooter(),
        ],
      ),
    );
  }
}

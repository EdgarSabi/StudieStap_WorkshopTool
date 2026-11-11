import 'package:flutter/material.dart';

import '../../theme/app_text.dart';
import '../../theme/app_theme.dart';
import '../auth/auth_decor.dart';
import '../auth/auth_form.dart';
import '../auth/auth_scaffold.dart';

/// Inlogscherm uit de Figma-frames "2. Login" (desktop en mobiel, licht en
/// donker).
class LoginPage extends StatefulWidget {
  const LoginPage({
    super.key,
    required this.onToggleTheme,
    required this.onLogin,
    required this.onForgotPassword,
    required this.onRegister,
  });

  final VoidCallback onToggleTheme;
  final void Function(String email, String password) onLogin;
  final VoidCallback onForgotPassword;
  final VoidCallback onRegister;

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _email = TextEditingController();
  final _password = TextEditingController();

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  void _submit() => widget.onLogin(_email.text.trim(), _password.text);

  @override
  Widget build(BuildContext context) {
    return AuthScaffold(
      desktop: _desktopScene,
      mobile: _mobileScene,
      onToggleTheme: widget.onToggleTheme,
      cardBuilder: (context, layout) => AuthCard(
        layout: layout,
        title: 'Inloggen',
        subtitle: 'Log in met je StudieStap-account',
        children: [
          AuthField(
            label: 'E-mailadres',
            hint: 'naam@studiestap.com',
            controller: _email,
            keyboardType: TextInputType.emailAddress,
            autofillHints: const [AutofillHints.email],
            textInputAction: TextInputAction.next,
          ),
          AuthField(
            label: 'Wachtwoord',
            hint: '••••••••',
            controller: _password,
            obscureText: true,
            autofillHints: const [AutofillHints.password],
            textInputAction: TextInputAction.done,
            onSubmitted: (_) => _submit(),
          ),
          Align(
            alignment: Alignment.centerRight,
            child: AuthTextLink(
              label: 'Wachtwoord vergeten?',
              style: inter(12, FontWeight.w600, context.colors.text),
              onPressed: widget.onForgotPassword,
            ),
          ),
          AuthSubmitButton(
            layout: layout,
            label: 'Inloggen',
            onPressed: _submit,
          ),
          Center(
            child: AuthTextLink.footer(
              context,
              layout: layout,
              label: 'Nog geen account? Registreer je',
              onPressed: widget.onRegister,
            ),
          ),
        ],
      ),
    );
  }
}

const _desktopScene = AuthScene(
  minHeight: 640,
  decor: [
    ...desktopBackdrop,
    SparkleDecor('sparkle_1', Offset(574, 264), 28, startsLarge: true),
    SparkleDecor('sparkle_2', Offset(895, 765), 30),
    SparkleDecor('sparkle_3', Offset(864, 153.6), 20),
    SparkleDecor('sparkle_4', Offset(432, 563.2), 22),
    StarDecor(Offset(645.92, 841.42), 22),
  ],
  mascot: AuthMascot(
    asset: 'mascotte_bye',
    center: Offset(192.25, 482.54),
    size: Size(264.5, 285.08),
    lift: 8,
  ),
);

const _mobileScene = AuthScene(
  minHeight: 760,
  decor: [
    ...mobileGlows,
    BookStackDecor(
      center: Offset(31.55, 681.3),
      rotation: 4,
      scale: mobileBookScale,
      books: booksLeft,
    ),
    BookStackDecor(
      center: Offset(304.31, 145.76),
      rotation: -5,
      scale: mobileBookScale,
      books: booksRight,
    ),
    BookStackDecor(
      center: Offset(308.95, 766.91),
      rotation: 6,
      scale: mobileSmallBookScale,
      books: booksBottom,
    ),
    SparkleDecor(
      'sparkle_1',
      Offset(153.13, 203.13),
      26.258,
      startsLarge: true,
    ),
    SparkleDecor('sparkle_2', Offset(244.07, 644.07), 28.133),
    SparkleDecor('sparkle_3', Offset(189.38, 129.38), 18.756),
    SparkleDecor('sparkle_4', Offset(120.32, 640.32), 20.631),
    StarDecor(Offset(173.55, 693.71), 20.631),
  ],
  mascot: AuthMascot(
    asset: 'mascotte_bye',
    center: Offset(80, 164.67),
    size: Size(120, 129.34),
    lift: 5.6,
  ),
);

import 'package:flutter/material.dart';

import '../auth/auth_decor.dart';
import '../auth/auth_form.dart';
import '../auth/auth_scaffold.dart';

/// Registratiescherm uit de Figma-frames "3. Registreren" (desktop en mobiel,
/// licht en donker).
class RegisterPage extends StatefulWidget {
  const RegisterPage({
    super.key,
    required this.onToggleTheme,
    required this.onRegister,
    required this.onLogin,
  });

  final VoidCallback onToggleTheme;
  final void Function(String name, String email, String password) onRegister;
  final VoidCallback onLogin;

  @override
  State<RegisterPage> createState() => _RegisterPageState();
}

class _RegisterPageState extends State<RegisterPage> {
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _confirm = TextEditingController();

  /// Pas na een poging tot registreren melden we dat de wachtwoorden
  /// verschillen, niet al tijdens het typen.
  bool _showMismatch = false;

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    _password.dispose();
    _confirm.dispose();
    super.dispose();
  }

  bool get _passwordsMatch => _password.text == _confirm.text;

  void _submit() {
    if (!_passwordsMatch) {
      setState(() => _showMismatch = true);
      return;
    }
    widget.onRegister(_name.text.trim(), _email.text.trim(), _password.text);
  }

  void _clearMismatch(String _) {
    if (_showMismatch && _passwordsMatch) {
      setState(() => _showMismatch = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AuthScaffold(
      desktop: _desktopScene,
      mobile: _mobileScene,
      onToggleTheme: widget.onToggleTheme,
      cardBuilder: (context, layout) => AuthCard(
        layout: layout,
        title: 'Account aanmaken',
        subtitle: 'Registreer je als StudieStapper',
        children: [
          AuthField(
            label: 'Naam',
            hint: 'Voor- en achternaam',
            controller: _name,
            keyboardType: TextInputType.name,
            textCapitalization: TextCapitalization.words,
            autofillHints: const [AutofillHints.name],
            textInputAction: TextInputAction.next,
          ),
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
            hint: 'Kies een wachtwoord',
            controller: _password,
            obscureText: true,
            autofillHints: const [AutofillHints.newPassword],
            textInputAction: TextInputAction.next,
            onChanged: _clearMismatch,
          ),
          AuthField(
            label: 'Bevestig wachtwoord',
            hint: 'Herhaal je wachtwoord',
            controller: _confirm,
            obscureText: true,
            autofillHints: const [AutofillHints.newPassword],
            textInputAction: TextInputAction.done,
            errorText: _showMismatch
                ? 'De wachtwoorden komen niet overeen'
                : null,
            onChanged: _clearMismatch,
            onSubmitted: (_) => _submit(),
          ),
          AuthSubmitButton(
            layout: layout,
            label: 'Account aanmaken',
            onPressed: _submit,
          ),
          Center(
            child: AuthTextLink.footer(
              context,
              layout: layout,
              label: 'Heb je al een account? Log in',
              onPressed: widget.onLogin,
            ),
          ),
        ],
      ),
    );
  }
}

const _desktopScene = AuthScene(
  minHeight: 720,
  decor: [
    ...desktopBackdrop,
    SparkleDecor('sparkle_1', Offset(474, 304), 28, startsLarge: true),
    SparkleDecor('sparkle_2', Offset(965, 715), 30),
    SparkleDecor('sparkle_3', Offset(864, 153.6), 20),
    SparkleDecor('sparkle_4', Offset(432, 563.2), 22),
    StarDecor(Offset(645.92, 841.42), 22),
    SwayDecor('plantje', Offset(158, 691.77), 96),
    SparkleDecor('sparkle_groot', Offset(245, 688.36), 30, startsLarge: true),
    SparkleDecor('sparkle_klein', Offset(69, 624.64), 18, startsLarge: true),
  ],
  mascot: AuthMascot(
    asset: 'mascotte_happy',
    center: Offset(181.23, 483.75),
    size: Size(242.46, 287.5),
    lift: 8,
  ),
);

const _mobileScene = AuthScene(
  // Lager dan het Figma-frame schuift de mascotte over de merknaam.
  minHeight: 844,
  decor: [
    ...mobileGlows,
    BookStackDecor(
      center: Offset(85.54, 743.92),
      rotation: 4,
      scale: mobileBookScale,
      books: booksLeft,
    ),
    BookStackDecor(
      center: Offset(304.31, 75.76),
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
      Offset(153.13, 133.13),
      26.258,
      startsLarge: true,
    ),
    SparkleDecor('sparkle_2', Offset(244.07, 704.07), 28.133),
    SparkleDecor('sparkle_3', Offset(189.38, 129.38), 18.756),
    SparkleDecor('sparkle_4', Offset(200.32, 700.32), 20.631),
    StarDecor(Offset(198.37, 731.95), 20.631),
    SwayDecor('plantje', Offset(220, 780), 60),
    SparkleDecor('sparkle_groot', Offset(279.5, 699.5), 19, startsLarge: true),
    SparkleDecor('sparkle_klein', Offset(35.5, 535.5), 11, startsLarge: true),
  ],
  mascot: AuthMascot(
    asset: 'mascotte_happy',
    center: Offset(74.82, 105),
    size: Size(109.63, 130),
    lift: 5.6,
  ),
);

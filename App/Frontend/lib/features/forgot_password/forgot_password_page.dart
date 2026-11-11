import 'package:flutter/material.dart';

import '../auth/auth_decor.dart';
import '../auth/auth_form.dart';
import '../auth/auth_scaffold.dart';

/// Scherm uit de Figma-frames "2a. Wachtwoord vergeten" (desktop en mobiel,
/// licht en donker).
class ForgotPasswordPage extends StatefulWidget {
  const ForgotPasswordPage({
    super.key,
    required this.onToggleTheme,
    required this.onSendResetLink,
    required this.onBackToLogin,
  });

  final VoidCallback onToggleTheme;
  final void Function(String email) onSendResetLink;
  final VoidCallback onBackToLogin;

  @override
  State<ForgotPasswordPage> createState() => _ForgotPasswordPageState();
}

class _ForgotPasswordPageState extends State<ForgotPasswordPage> {
  final _email = TextEditingController();

  @override
  void dispose() {
    _email.dispose();
    super.dispose();
  }

  void _submit() => widget.onSendResetLink(_email.text.trim());

  @override
  Widget build(BuildContext context) {
    return AuthScaffold(
      desktop: _desktopScene,
      mobile: _mobileScene,
      onToggleTheme: widget.onToggleTheme,
      cardBuilder: (context, layout) => AuthCard(
        layout: layout,
        title: 'Wachtwoord vergeten?',
        subtitle:
            'Vul je e-mailadres in en we sturen je een link om je wachtwoord '
            'opnieuw in te stellen.',
        children: [
          AuthField(
            label: 'E-mailadres',
            hint: 'naam@studiestap.com',
            controller: _email,
            keyboardType: TextInputType.emailAddress,
            autofillHints: const [AutofillHints.email],
            textInputAction: TextInputAction.done,
            onSubmitted: (_) => _submit(),
          ),
          AuthSubmitButton(
            layout: layout,
            label: 'Verstuur reset-link',
            onPressed: _submit,
          ),
          Center(
            child: AuthTextLink.footer(
              context,
              layout: layout,
              label: '← Terug naar inloggen',
              onPressed: widget.onBackToLogin,
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
    SparkleDecor('sparkle_1', Offset(576, 307.2), 28, startsLarge: true),
    SparkleDecor('sparkle_2', Offset(892.8, 716.8), 30),
    SparkleDecor('sparkle_3', Offset(864, 153.6), 20),
    SparkleDecor('sparkle_4', Offset(432, 563.2), 22),
    StarDecor(Offset(645.92, 841.42), 22),
    TiltedDecor('sleutel', Offset(1118.69, 409.47), 96, 20),
    TiltedDecor('slot', Offset(1329.53, 512.48), 70, -8),
    SparkleDecor('sparkle_roze', Offset(1243, 390.26), 26),
  ],
  mascot: AuthMascot(
    asset: 'mascotte_shy',
    center: Offset(176.05, 483.75),
    size: Size(232.1, 287.5),
    lift: 8,
    offsetPhase: true,
  ),
);

const _mobileScene = AuthScene(
  minHeight: 720,
  decor: [
    ...mobileGlows,
    BookStackDecor(
      center: Offset(31.55, 681.3),
      rotation: 4,
      scale: mobileBookScale,
      books: booksLeft,
    ),
    BookStackDecor(
      center: Offset(360.12, 177.67),
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
    SparkleDecor('sparkle_1', Offset(156, 253.2), 26.258, startsLarge: true),
    SparkleDecor('sparkle_2', Offset(244.07, 594.07), 28.133),
    SparkleDecor('sparkle_3', Offset(234, 126.6), 18.756),
    SparkleDecor('sparkle_4', Offset(120.32, 590.32), 20.631),
    StarDecor(Offset(173.55, 693.71), 20.631),
    TiltedDecor('sleutel', Offset(287.93, 618.45), 60, 20),
    TiltedDecor('slot', Offset(364.28, 598.3), 43, -8),
    SparkleDecor('sparkle_roze', Offset(208, 588), 16),
  ],
  mascot: AuthMascot(
    asset: 'mascotte_shy',
    center: Offset(72.48, 215),
    size: Size(104.95, 130),
    lift: 5.6,
    offsetPhase: true,
  ),
);

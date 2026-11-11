import 'package:flutter/material.dart';

import '../../theme/app_text.dart';
import '../../theme/app_theme.dart';
import '../../widgets/primary_button.dart';
import 'auth_scaffold.dart';

const _borderWidth = 1.5;

/// Witte kaart met titel en ondertitel, gevolgd door [children].
class AuthCard extends StatelessWidget {
  const AuthCard({
    super.key,
    required this.layout,
    required this.title,
    required this.subtitle,
    required this.children,
  });

  final AuthLayout layout;
  final String title;
  final String subtitle;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return Container(
      padding: layout.cardPadding - const EdgeInsets.all(_borderWidth),
      decoration: BoxDecoration(
        color: colors.card,
        borderRadius: BorderRadius.circular(layout.cardRadius),
        border: Border.all(color: colors.cardBorder, width: _borderWidth),
        boxShadow: [
          BoxShadow(
            color: colors.cardShadow,
            offset: const Offset(0, 6),
            blurRadius: 18,
          ),
        ],
      ),
      child: AutofillGroup(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          spacing: layout.cardGap,
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              spacing: 4,
              children: [
                Semantics(
                  header: true,
                  child: Text(
                    title,
                    style: inter(
                      layout.titleSize,
                      FontWeight.w700,
                      layout.isCompact
                          ? colors.titleMobile
                          : colors.titleDesktop,
                    ),
                  ),
                ),
                Text(
                  subtitle,
                  style: inter(
                    layout.subtitleSize,
                    FontWeight.w400,
                    colors.textMuted,
                  ),
                ),
              ],
            ),
            ...children,
          ],
        ),
      ),
    );
  }
}

/// Invoerveld met een label erboven.
class AuthField extends StatelessWidget {
  const AuthField({
    super.key,
    required this.label,
    required this.hint,
    required this.controller,
    required this.autofillHints,
    required this.textInputAction,
    this.keyboardType,
    this.textCapitalization = TextCapitalization.none,
    this.obscureText = false,
    this.errorText,
    this.onChanged,
    this.onSubmitted,
  });

  final String label;
  final String hint;
  final TextEditingController controller;
  final Iterable<String> autofillHints;
  final TextInputAction textInputAction;
  final TextInputType? keyboardType;
  final TextCapitalization textCapitalization;
  final bool obscureText;
  final String? errorText;
  final ValueChanged<String>? onChanged;
  final ValueChanged<String>? onSubmitted;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final error = Theme.of(context).colorScheme.error;
    OutlineInputBorder border(Color color) => OutlineInputBorder(
      borderRadius: BorderRadius.circular(14),
      borderSide: BorderSide(color: color, width: _borderWidth),
    );
    // Samengevoegd zodat schermlezers het label bij het veld voorlezen.
    return MergeSemantics(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        spacing: 6,
        children: [
          Text(label, style: inter(12, FontWeight.w600, colors.text)),
          TextField(
            controller: controller,
            obscureText: obscureText,
            keyboardType: keyboardType,
            textCapitalization: textCapitalization,
            autofillHints: autofillHints,
            textInputAction: textInputAction,
            onChanged: onChanged,
            onSubmitted: onSubmitted,
            cursorColor: colors.primary,
            style: inter(13, FontWeight.w400, colors.text),
            decoration: InputDecoration(
              hintText: hint,
              hintStyle: inter(13, FontWeight.w400, colors.inputHint),
              errorText: errorText,
              errorStyle: inter(12, FontWeight.w400, error),
              isDense: true,
              filled: true,
              fillColor: colors.inputFill,
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 14 + _borderWidth,
                vertical: 12 + _borderWidth,
              ),
              enabledBorder: border(colors.cardBorder),
              focusedBorder: border(colors.primary),
              errorBorder: border(error),
              focusedErrorBorder: border(error),
            ),
          ),
        ],
      ),
    );
  }
}

/// Groene knop over de volle breedte van de kaart.
class AuthSubmitButton extends StatelessWidget {
  const AuthSubmitButton({
    super.key,
    required this.layout,
    required this.label,
    required this.onPressed,
  });

  final AuthLayout layout;
  final String label;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return PrimaryButton(
      label: label,
      onPressed: onPressed,
      padding: layout.buttonPadding,
      radius: layout.buttonRadius,
      fontSize: 14,
    );
  }
}

/// Tekstlink zonder extra ruimte eromheen.
class AuthTextLink extends StatelessWidget {
  const AuthTextLink({
    super.key,
    required this.label,
    required this.style,
    required this.onPressed,
  });

  final String label;
  final TextStyle style;
  final VoidCallback onPressed;

  /// De gecentreerde link onderaan de kaart.
  factory AuthTextLink.footer(
    BuildContext context, {
    required AuthLayout layout,
    required String label,
    required VoidCallback onPressed,
  }) {
    return AuthTextLink(
      label: label,
      style: inter(
        layout.footerSize,
        FontWeight.w400,
        context.colors.textMuted,
      ),
      onPressed: onPressed,
    );
  }

  @override
  Widget build(BuildContext context) {
    return TextButton(
      onPressed: onPressed,
      style: TextButton.styleFrom(
        foregroundColor: style.color,
        padding: EdgeInsets.zero,
        minimumSize: Size.zero,
        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
        textStyle: style,
      ),
      child: Text(label, textAlign: TextAlign.center),
    );
  }
}

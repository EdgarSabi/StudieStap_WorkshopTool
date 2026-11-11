import 'package:flutter/material.dart';

import '../theme/app_text.dart';
import '../theme/app_theme.dart';

/// Groene hoofdknop met schaduw uit het Figma-ontwerp.
class PrimaryButton extends StatelessWidget {
  const PrimaryButton({
    super.key,
    required this.label,
    required this.onPressed,
    required this.padding,
    required this.radius,
    required this.fontSize,
  });

  final String label;
  final VoidCallback onPressed;
  final EdgeInsets padding;
  final double radius;
  final double fontSize;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final borderRadius = BorderRadius.circular(radius);
    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: borderRadius,
        boxShadow: [
          BoxShadow(
            color: colors.primaryShadow,
            offset: const Offset(0, 4),
            blurRadius: 10,
          ),
        ],
      ),
      child: Material(
        color: colors.primary,
        borderRadius: borderRadius,
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onPressed,
          child: Padding(
            padding: padding,
            child: Text(
              label,
              textAlign: TextAlign.center,
              style: inter(fontSize, FontWeight.w600, Colors.white),
            ),
          ),
        ),
      ),
    );
  }
}

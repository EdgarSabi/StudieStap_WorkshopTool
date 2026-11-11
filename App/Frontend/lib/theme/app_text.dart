import 'package:flutter/material.dart';

/// Tekststijl uit Figma: regelhoogte "normal" van Inter, zonder de regelhoogte
/// en letterafstand die Material anders meegeeft.
TextStyle inter(
  double size,
  FontWeight weight,
  Color color, {
  double spacing = 0,
}) {
  return TextStyle(
    fontFamily: 'Inter',
    fontSize: size,
    fontWeight: weight,
    color: color,
    height: 1.21,
    letterSpacing: spacing,
  );
}

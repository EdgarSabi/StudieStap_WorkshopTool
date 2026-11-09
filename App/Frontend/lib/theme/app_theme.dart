import 'package:flutter/material.dart';

/// Kleuren uit het Figma-ontwerp. Als [ThemeExtension] zodat ze meeanimeren
/// wanneer de gebruiker van thema wisselt.
@immutable
class AppColors extends ThemeExtension<AppColors> {
  const AppColors({
    required this.skyTop,
    required this.skyBottom,
    required this.text,
    required this.textMuted,
    required this.titleDesktop,
    required this.titleMobile,
    required this.primary,
    required this.primaryShadow,
    required this.card,
    required this.cardBorder,
    required this.cardShadow,
    required this.toggleShadow,
  });

  final Color skyTop;
  final Color skyBottom;
  final Color text;
  final Color textMuted;
  final Color titleDesktop;
  final Color titleMobile;
  final Color primary;
  final Color primaryShadow;
  final Color card;
  final Color cardBorder;
  final Color cardShadow;
  final Color toggleShadow;

  static const light = AppColors(
    skyTop: Color(0xFFD6EDFB),
    skyBottom: Color(0xFFEAF6EC),
    text: Color(0xFF1D3A24),
    textMuted: Color(0xFF5D7A63),
    titleDesktop: Color(0xFF1B5E20),
    titleMobile: Color(0xFF1D3A24),
    primary: Color(0xFF43A047),
    primaryShadow: Color(0x592E7D33),
    card: Color(0xF5FFFFFF),
    cardBorder: Color(0xFFBFE0BF),
    cardShadow: Color(0x292E7D33),
    toggleShadow: Color(0x292E7D33),
  );

  static const dark = AppColors(
    skyTop: Color(0xFF0D2535),
    skyBottom: Color(0xFF10301F),
    text: Color(0xFFE8F5E9),
    textMuted: Color(0xFFA4BBA9),
    titleDesktop: Color(0xFFA5D6A7),
    titleMobile: Color(0xFFE8F5E9),
    primary: Color(0xFF4CAF50),
    primaryShadow: Color(0x66000000),
    card: Color(0xF012301F),
    cardBorder: Color(0xFF2F5A3E),
    cardShadow: Color(0x66000000),
    toggleShadow: Color(0x66000000),
  );

  @override
  AppColors copyWith({
    Color? skyTop,
    Color? skyBottom,
    Color? text,
    Color? textMuted,
    Color? titleDesktop,
    Color? titleMobile,
    Color? primary,
    Color? primaryShadow,
    Color? card,
    Color? cardBorder,
    Color? cardShadow,
    Color? toggleShadow,
  }) {
    return AppColors(
      skyTop: skyTop ?? this.skyTop,
      skyBottom: skyBottom ?? this.skyBottom,
      text: text ?? this.text,
      textMuted: textMuted ?? this.textMuted,
      titleDesktop: titleDesktop ?? this.titleDesktop,
      titleMobile: titleMobile ?? this.titleMobile,
      primary: primary ?? this.primary,
      primaryShadow: primaryShadow ?? this.primaryShadow,
      card: card ?? this.card,
      cardBorder: cardBorder ?? this.cardBorder,
      cardShadow: cardShadow ?? this.cardShadow,
      toggleShadow: toggleShadow ?? this.toggleShadow,
    );
  }

  @override
  AppColors lerp(AppColors? other, double t) {
    if (other == null) return this;
    return AppColors(
      skyTop: Color.lerp(skyTop, other.skyTop, t)!,
      skyBottom: Color.lerp(skyBottom, other.skyBottom, t)!,
      text: Color.lerp(text, other.text, t)!,
      textMuted: Color.lerp(textMuted, other.textMuted, t)!,
      titleDesktop: Color.lerp(titleDesktop, other.titleDesktop, t)!,
      titleMobile: Color.lerp(titleMobile, other.titleMobile, t)!,
      primary: Color.lerp(primary, other.primary, t)!,
      primaryShadow: Color.lerp(primaryShadow, other.primaryShadow, t)!,
      card: Color.lerp(card, other.card, t)!,
      cardBorder: Color.lerp(cardBorder, other.cardBorder, t)!,
      cardShadow: Color.lerp(cardShadow, other.cardShadow, t)!,
      toggleShadow: Color.lerp(toggleShadow, other.toggleShadow, t)!,
    );
  }
}

ThemeData _buildTheme(Brightness brightness, AppColors colors) {
  return ThemeData(
    brightness: brightness,
    fontFamily: 'Inter',
    colorScheme: ColorScheme.fromSeed(
      seedColor: colors.primary,
      brightness: brightness,
    ),
    extensions: [colors],
  );
}

final lightTheme = _buildTheme(Brightness.light, AppColors.light);
final darkTheme = _buildTheme(Brightness.dark, AppColors.dark);

extension AppColorsContext on BuildContext {
  AppColors get colors => Theme.of(this).extension<AppColors>()!;
}

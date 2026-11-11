import 'package:flutter/material.dart';

/// Kleuren uit het Figma-ontwerp. Als [ThemeExtension] zodat ze meeanimeren
/// wanneer de gebruiker van thema wisselt.
@immutable
class AppColors extends ThemeExtension<AppColors> {
  const AppColors({
    required this.skyTop,
    required this.skyBottom,
    required this.pageTop,
    required this.pageBottom,
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
    required this.inputFill,
    required this.inputHint,
    required this.bookPages,
    required this.bookCoral,
    required this.bookLightGreen,
    required this.bookPink,
    required this.bookOrange,
    required this.bookLime,
  });

  /// Achtergrond van de landingspagina.
  final Color skyTop;
  final Color skyBottom;

  /// Achtergrond van de schermen met een kaart in het midden, zoals inloggen.
  final Color pageTop;
  final Color pageBottom;

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

  /// Invoervelden; de rand gebruikt [cardBorder].
  final Color inputFill;
  final Color inputHint;

  /// Decoratieve boekenstapels. Groen, geel en donkergroen zijn in beide
  /// thema's gelijk; de overige kleuren verschillen per thema.
  final Color bookPages;
  final Color bookCoral;
  final Color bookLightGreen;
  final Color bookPink;
  final Color bookOrange;
  final Color bookLime;

  static const light = AppColors(
    skyTop: Color(0xFFD6EDFB),
    skyBottom: Color(0xFFEAF6EC),
    pageTop: Color(0xFFFFF6EA),
    pageBottom: Color(0xFFF1F8E6),
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
    inputFill: Color(0xFFF2F9EC),
    inputHint: Color(0xFF8AA690),
    bookPages: Color(0xFFFFF6E8),
    bookCoral: Color(0xFFF4756B),
    bookLightGreen: Color(0xFF81C784),
    bookPink: Color(0xFFF58FB0),
    bookOrange: Color(0xFFF6A04D),
    bookLime: Color(0xFFA8D84A),
  );

  static const dark = AppColors(
    skyTop: Color(0xFF0D2535),
    skyBottom: Color(0xFF10301F),
    pageTop: Color(0xFF0D281B),
    pageBottom: Color(0xFF0F2D1E),
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
    inputFill: Color(0xFF173A27),
    inputHint: Color(0xFF86A38D),
    bookPages: Color(0xFF382B18),
    bookCoral: Color(0xFFF15044),
    bookLightGreen: Color(0xFF66BB69),
    bookPink: Color(0xFF6F3044),
    bookOrange: Color(0xFFF48C28),
    bookLime: Color(0xFF9AD22D),
  );

  @override
  AppColors copyWith({
    Color? skyTop,
    Color? skyBottom,
    Color? pageTop,
    Color? pageBottom,
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
    Color? inputFill,
    Color? inputHint,
    Color? bookPages,
    Color? bookCoral,
    Color? bookLightGreen,
    Color? bookPink,
    Color? bookOrange,
    Color? bookLime,
  }) {
    return AppColors(
      skyTop: skyTop ?? this.skyTop,
      skyBottom: skyBottom ?? this.skyBottom,
      pageTop: pageTop ?? this.pageTop,
      pageBottom: pageBottom ?? this.pageBottom,
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
      inputFill: inputFill ?? this.inputFill,
      inputHint: inputHint ?? this.inputHint,
      bookPages: bookPages ?? this.bookPages,
      bookCoral: bookCoral ?? this.bookCoral,
      bookLightGreen: bookLightGreen ?? this.bookLightGreen,
      bookPink: bookPink ?? this.bookPink,
      bookOrange: bookOrange ?? this.bookOrange,
      bookLime: bookLime ?? this.bookLime,
    );
  }

  @override
  AppColors lerp(AppColors? other, double t) {
    if (other == null) return this;
    Color mix(Color a, Color b) => Color.lerp(a, b, t)!;
    return AppColors(
      skyTop: mix(skyTop, other.skyTop),
      skyBottom: mix(skyBottom, other.skyBottom),
      pageTop: mix(pageTop, other.pageTop),
      pageBottom: mix(pageBottom, other.pageBottom),
      text: mix(text, other.text),
      textMuted: mix(textMuted, other.textMuted),
      titleDesktop: mix(titleDesktop, other.titleDesktop),
      titleMobile: mix(titleMobile, other.titleMobile),
      primary: mix(primary, other.primary),
      primaryShadow: mix(primaryShadow, other.primaryShadow),
      card: mix(card, other.card),
      cardBorder: mix(cardBorder, other.cardBorder),
      cardShadow: mix(cardShadow, other.cardShadow),
      toggleShadow: mix(toggleShadow, other.toggleShadow),
      inputFill: mix(inputFill, other.inputFill),
      inputHint: mix(inputHint, other.inputHint),
      bookPages: mix(bookPages, other.bookPages),
      bookCoral: mix(bookCoral, other.bookCoral),
      bookLightGreen: mix(bookLightGreen, other.bookLightGreen),
      bookPink: mix(bookPink, other.bookPink),
      bookOrange: mix(bookOrange, other.bookOrange),
      bookLime: mix(bookLime, other.bookLime),
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

import 'package:flutter/painting.dart';

// Decoratie van de inlog-, registratie- en wachtwoordschermen. Alle
// coördinaten zijn middelpunten in het Figma-frame (1440 × 1024 voor desktop,
// 390 × 844 voor mobiel); de SVG's staan in assets/auth/<desktop|mobile>/.

/// Eén decoratief element. De volgorde in een lijst is de tekenvolgorde.
sealed class AuthDecor {
  const AuthDecor();
}

/// Zachte gloed die meerekt met het scherm en zachtjes pulseert.
class GlowDecor extends AuthDecor {
  const GlowDecor(this.asset, this.center, this.size);

  final String asset;
  final Offset center;
  final Size size;
}

/// Sparkle die groter en kleiner wordt en in- en uitfaadt. Sparkles in fase A
/// beginnen groot, die in fase B klein. De rust-opacity zit in de SVG.
class SparkleDecor extends AuthDecor {
  const SparkleDecor(
    this.asset,
    this.center,
    this.size, {
    this.startsLarge = false,
  });

  final String asset;
  final Offset center;
  final double size;
  final bool startsLarge;
}

/// Groene ster, 10° gedraaid, pulseert in fase A.
class StarDecor extends AuthDecor {
  const StarDecor(this.center, this.box);

  final Offset center;

  /// Zijde van het vierkante vak waarin de ster met marge zit.
  final double box;
}

/// Element dat heen en weer wiegt (±5°), zoals het plantje.
class SwayDecor extends AuthDecor {
  const SwayDecor(this.asset, this.center, this.size);

  final String asset;
  final Offset center;
  final double size;
}

/// Stilstaand element onder een vaste hoek, zoals de sleutel en het slot.
class TiltedDecor extends AuthDecor {
  const TiltedDecor(this.asset, this.center, this.size, this.rotation);

  final String asset;
  final Offset center;
  final double size;

  /// Graden, met de klok mee.
  final double rotation;
}

/// Stapel boeken, van boven naar beneden.
class BookStackDecor extends AuthDecor {
  const BookStackDecor({
    required this.center,
    required this.rotation,
    required this.books,
    this.scale = 1,
  });

  static const bookHeight = 34.0;
  static const stackWidth = 190.0;

  final Offset center;

  /// Graden, met de klok mee.
  final double rotation;

  /// Boekmaten zijn in eenheden van een stapel op schaal 1.
  final double scale;
  final List<Book> books;

  Size get size => Size(stackWidth, bookHeight * books.length);
}

enum BookColor {
  green,
  yellow,
  darkGreen,
  coral,
  lightGreen,
  pink,
  orange,
  lime,
}

class Book {
  const Book(this.left, this.width, this.color);

  final double left;
  final double width;
  final BookColor color;
}

// De vier stapels komen op alle schermen terug, op mobiel soms verschoven.
const booksLeft = [
  Book(-7, 184, BookColor.darkGreen),
  Book(11.5, 187, BookColor.yellow),
  Book(10, 150, BookColor.green),
];
const booksRight = [
  Book(14.5, 181, BookColor.pink),
  Book(-7, 184, BookColor.green),
  Book(11.5, 187, BookColor.lightGreen),
  Book(10, 150, BookColor.coral),
];
const booksBottom = [
  Book(11.5, 187, BookColor.orange),
  Book(10, 150, BookColor.darkGreen),
];
const booksTop = [
  Book(11.5, 187, BookColor.coral),
  Book(10, 150, BookColor.lime),
];

/// Gloed en boekenstapels die op elk desktopscherm gelijk zijn.
const desktopBackdrop = <AuthDecor>[
  GlowDecor('gloed_links', Offset(288, 102.4), Size(960, 636)),
  GlowDecor('gloed_rechts', Offset(1296, 921.6), Size(960, 636)),
  BookStackDecor(center: Offset(125.81, 825.7), rotation: 4, books: booksLeft),
  BookStackDecor(
    center: Offset(1315.97, 216.74),
    rotation: -5,
    books: booksRight,
  ),
  BookStackDecor(
    center: Offset(1263.12, 880.14),
    rotation: 6,
    books: booksBottom,
  ),
  BookStackDecor(center: Offset(175.83, 194.68), rotation: -6, books: booksTop),
];

const mobileGlows = <AuthDecor>[
  GlowDecor('gloed_links', Offset(78, 84.4), Size(324, 596.4)),
  GlowDecor('gloed_rechts', Offset(351, 759.6), Size(324, 596.4)),
];

/// Schaal van de mobiele boekenstapels ten opzichte van desktop.
const mobileBookScale = 0.9378;
const mobileSmallBookScale = 0.75;

/// Mascotte die rustig op en neer deint en een beetje kantelt.
class AuthMascot {
  const AuthMascot({
    required this.asset,
    required this.center,
    required this.size,
    required this.lift,
    this.offsetPhase = false,
  });

  /// Bestandsnaam zonder extensie in assets/auth/.
  final String asset;
  final Offset center;
  final Size size;

  /// Hoeveel pixels de mascotte omhoog deint.
  final double lift;

  /// De verlegen mascotte beweegt een kwart lus later dan de andere.
  final bool offsetPhase;

  String get path => 'assets/auth/$asset.png';
}

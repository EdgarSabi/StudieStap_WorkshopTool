import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../../theme/app_text.dart';
import '../../theme/app_theme.dart';
import '../../widgets/theme_toggle.dart';
import 'auth_decor.dart';

const _mobileBreakpoint = 800.0;

/// Alle decoratie beweegt in één lus van 6 s, zoals in het Figma-prototype.
const _loopDuration = Duration(seconds: 6);

/// Maten die op alle schermen met een kaart in het midden gelijk zijn.
class AuthLayout {
  const AuthLayout._({
    required this.folder,
    required this.designSize,
    required this.scalesVertically,
    required this.isCompact,
    required this.brandLeft,
    required this.brandTop,
    required this.brandSize,
    required this.toggleTop,
    required this.toggleRight,
    required this.toggleSize,
    required this.cardWidth,
    required this.sideMargin,
    required this.cardPadding,
    required this.cardRadius,
    required this.cardGap,
    required this.titleSize,
    required this.subtitleSize,
    required this.buttonPadding,
    required this.buttonRadius,
    required this.footerSize,
  });

  final String folder;
  final Size designSize;

  /// Desktop schaalt de decoratie mee met de hoogte. Mobiel houdt de vaste
  /// afstand tot het midden, zodat de mascotte bij de kaart blijft.
  final bool scalesVertically;
  final bool isCompact;
  final double brandLeft;
  final double brandTop;
  final double brandSize;
  final double toggleTop;
  final double toggleRight;
  final double toggleSize;
  final double cardWidth;
  final double sideMargin;
  final EdgeInsets cardPadding;
  final double cardRadius;
  final double cardGap;
  final double titleSize;
  final double subtitleSize;
  final EdgeInsets buttonPadding;
  final double buttonRadius;
  final double footerSize;

  String svgPath(String name) => 'assets/auth/$folder/$name.svg';

  /// De themaknop is dezelfde als op de landingspagina.
  String toggleAsset(bool isDark) =>
      'assets/landing/$folder/${isDark ? 'dark' : 'light'}/modus_wissel.svg';

  static const desktop = AuthLayout._(
    folder: 'desktop',
    designSize: Size(1440, 1024),
    scalesVertically: true,
    isCompact: false,
    brandLeft: 48,
    brandTop: 40,
    brandSize: 16,
    toggleTop: 16,
    toggleRight: 16,
    toggleSize: 44,
    cardWidth: 440,
    sideMargin: 24,
    cardPadding: EdgeInsets.all(48),
    cardRadius: 22,
    cardGap: 20,
    titleSize: 24,
    subtitleSize: 13,
    buttonPadding: EdgeInsets.symmetric(horizontal: 20, vertical: 14),
    buttonRadius: 22.5,
    footerSize: 13,
  );

  static const mobile = AuthLayout._(
    folder: 'mobile',
    designSize: Size(390, 844),
    scalesVertically: false,
    isCompact: true,
    brandLeft: 20,
    brandTop: 24,
    brandSize: 15,
    toggleTop: 14,
    toggleRight: 16,
    toggleSize: 36,
    cardWidth: 342,
    sideMargin: 16,
    cardPadding: EdgeInsets.symmetric(horizontal: 28, vertical: 32),
    cardRadius: 20,
    cardGap: 18,
    titleSize: 20,
    subtitleSize: 12,
    buttonPadding: EdgeInsets.symmetric(horizontal: 20, vertical: 13),
    buttonRadius: 21.5,
    footerSize: 12,
  );
}

/// De decoratie van één scherm in één formaat.
class AuthScene {
  const AuthScene({
    required this.decor,
    required this.mascot,
    required this.minHeight,
  });

  /// Getekend onder de kaart, in deze volgorde.
  final List<AuthDecor> decor;

  /// Getekend boven de kaart.
  final AuthMascot mascot;

  /// Onder deze hoogte gaat de pagina scrollen, zodat de kaart en de mascotte
  /// niet over de kop schuiven.
  final double minHeight;
}

/// Gedeelde opbouw van de inlog-, registratie- en wachtwoordschermen:
/// achtergrond, bewegende decoratie, merknaam, themaknop en een kaart in het
/// midden.
class AuthScaffold extends StatefulWidget {
  const AuthScaffold({
    super.key,
    required this.desktop,
    required this.mobile,
    required this.onToggleTheme,
    required this.cardBuilder,
  });

  final AuthScene desktop;
  final AuthScene mobile;
  final VoidCallback onToggleTheme;
  final Widget Function(BuildContext context, AuthLayout layout) cardBuilder;

  @override
  State<AuthScaffold> createState() => _AuthScaffoldState();
}

class _AuthScaffoldState extends State<AuthScaffold>
    with SingleTickerProviderStateMixin {
  late final AnimationController _loop = AnimationController(
    vsync: this,
    duration: _loopDuration,
  )..repeat();

  late final _motion = _AuthMotion(_loop);
  bool _assetsRequested = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_assetsRequested) {
      _assetsRequested = true;
      _precacheAssets();
    }
  }

  /// Laadt beide formaten vooraf, zodat wisselen niet knippert.
  void _precacheAssets() {
    final scenes = [
      (AuthLayout.desktop, widget.desktop),
      (AuthLayout.mobile, widget.mobile),
    ];
    final paths = <String>{};
    for (final (layout, scene) in scenes) {
      precacheImage(AssetImage(scene.mascot.path), context);
      paths.addAll([
        for (final decor in scene.decor)
          if (_assetOf(decor) case final name?) layout.svgPath(name),
        layout.toggleAsset(false),
        layout.toggleAsset(true),
      ]);
    }
    for (final path in paths) {
      final loader = SvgAssetLoader(path);
      svg.cache.putIfAbsent(
        loader.cacheKey(null),
        () => loader.loadBytes(null),
      );
    }
  }

  static String? _assetOf(AuthDecor decor) => switch (decor) {
    GlowDecor(:final asset) ||
    SparkleDecor(:final asset) ||
    SwayDecor(:final asset) ||
    TiltedDecor(:final asset) => asset,
    StarDecor() => 'ster',
    BookStackDecor() => null,
  };

  @override
  void dispose() {
    _loop.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      body: LayoutBuilder(
        builder: (context, constraints) {
          final isMobile = constraints.maxWidth < _mobileBreakpoint;
          final layout = isMobile ? AuthLayout.mobile : AuthLayout.desktop;
          final scene = isMobile ? widget.mobile : widget.desktop;
          final topInset = MediaQuery.paddingOf(context).top;
          final size = Size(
            constraints.maxWidth,
            math.max(constraints.maxHeight, scene.minHeight + topInset),
          );
          final frame = _Frame(layout, size);
          return SingleChildScrollView(
            child: SizedBox.fromSize(
              size: size,
              child: Stack(
                children: [
                  Positioned.fill(
                    child: DecoratedBox(
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                          colors: [colors.pageTop, colors.pageBottom],
                        ),
                      ),
                    ),
                  ),
                  Positioned.fill(
                    child: IgnorePointer(
                      child: RepaintBoundary(
                        child: _DecorLayer(
                          frame: frame,
                          decor: scene.decor,
                          motion: _motion,
                        ),
                      ),
                    ),
                  ),
                  Positioned(
                    left: layout.brandLeft,
                    top: layout.brandTop + topInset,
                    child: Text(
                      'AI-coach',
                      style: inter(
                        layout.brandSize,
                        FontWeight.w700,
                        colors.text,
                      ),
                    ),
                  ),
                  Center(
                    child: SizedBox(
                      width: math.min(
                        layout.cardWidth,
                        size.width - layout.sideMargin * 2,
                      ),
                      child: widget.cardBuilder(context, layout),
                    ),
                  ),
                  _Mascot(frame: frame, mascot: scene.mascot, motion: _motion),
                  Positioned(
                    top: layout.toggleTop + topInset,
                    right: layout.toggleRight,
                    child: ThemeToggle(
                      size: layout.toggleSize,
                      isDark: isDark,
                      asset: layout.toggleAsset(isDark),
                      onPressed: widget.onToggleTheme,
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}

/// Keyframes uit het Figma-prototype: vier stappen van 1,5 s, elk ease-in-out.
class _AuthMotion {
  _AuthMotion(AnimationController loop)
    : glow = _keyframes(loop, const [1, 0.6, 1, 0.6, 1]),
      scaleA = _keyframes(loop, const [1, 0.7, 1, 0.7, 1]),
      fadeA = _keyframes(loop, const [1, 0.3, 1, 0.3, 1]),
      scaleB = _keyframes(loop, const [0.7, 1, 0.7, 1, 0.7]),
      fadeB = _keyframes(loop, const [0.3, 1, 0.3, 1, 0.3]),
      sway = _keyframes(loop, const [-5, 0, 5, 0, -5]),
      mascotTilt = _keyframes(loop, const [-2.5, 0, 2.5, 0, -2.5]),
      mascotLift = _keyframes(loop, const [1, 0, 1, 0, 1]),
      shiftedTilt = _keyframes(loop, const [0, 2.5, 0, -2.5, 0]),
      shiftedLift = _keyframes(loop, const [0, 1, 0, 1, 0]);

  final Animation<double> glow;
  final Animation<double> scaleA;
  final Animation<double> fadeA;
  final Animation<double> scaleB;
  final Animation<double> fadeB;

  /// Graden.
  final Animation<double> sway;

  /// Kanteling in graden en deinen (1 is helemaal omhoog) van de mascotte.
  final Animation<double> mascotTilt;
  final Animation<double> mascotLift;
  final Animation<double> shiftedTilt;
  final Animation<double> shiftedLift;

  static Animation<double> _keyframes(
    AnimationController loop,
    List<double> values,
  ) {
    return loop.drive(
      TweenSequence([
        for (var i = 0; i < values.length - 1; i++)
          TweenSequenceItem(
            tween: Tween(
              begin: values[i],
              end: values[i + 1],
            ).chain(CurveTween(curve: Curves.easeInOut)),
            weight: 1,
          ),
      ]),
    );
  }
}

/// Zet Figma-coördinaten om naar het scherm. Horizontaal schaalt alles mee met
/// de breedte; verticaal bepaalt [AuthLayout.scalesVertically] het gedrag.
class _Frame {
  _Frame(this.layout, this.size)
    : scaleX = size.width / layout.designSize.width,
      scaleY = layout.scalesVertically
          ? size.height / layout.designSize.height
          : 1;

  final AuthLayout layout;
  final Size size;
  final double scaleX;
  final double scaleY;

  /// Schaal voor objecten die hun verhouding houden.
  double get uniform => math.min(scaleX, scaleY);

  Widget place({
    required Offset center,
    required Size size,
    required Widget child,
  }) {
    final x = center.dx * scaleX;
    final y =
        this.size.height / 2 +
        (center.dy - layout.designSize.height / 2) * scaleY;
    return Positioned(
      left: x - size.width / 2,
      top: y - size.height / 2,
      width: size.width,
      height: size.height,
      child: child,
    );
  }
}

class _DecorLayer extends StatelessWidget {
  const _DecorLayer({
    required this.frame,
    required this.decor,
    required this.motion,
  });

  final _Frame frame;
  final List<AuthDecor> decor;
  final _AuthMotion motion;

  @override
  Widget build(BuildContext context) {
    final colors = context.colors;
    return Stack(
      clipBehavior: Clip.none,
      children: [for (final item in decor) _build(item, colors)],
    );
  }

  Widget _build(AuthDecor item, AppColors colors) {
    final layout = frame.layout;
    final u = frame.uniform;
    switch (item) {
      case GlowDecor():
        return frame.place(
          center: item.center,
          size: Size(
            item.size.width * frame.scaleX,
            item.size.height * frame.scaleY,
          ),
          child: FadeTransition(
            opacity: motion.glow,
            child: SvgPicture.asset(
              layout.svgPath(item.asset),
              fit: BoxFit.fill,
            ),
          ),
        );
      case SparkleDecor():
        final size = item.size * u;
        return frame.place(
          center: item.center,
          size: Size.square(size),
          child: FadeTransition(
            opacity: item.startsLarge ? motion.fadeA : motion.fadeB,
            child: ScaleTransition(
              scale: item.startsLarge ? motion.scaleA : motion.scaleB,
              child: SvgPicture.asset(
                layout.svgPath(item.asset),
                width: size,
                height: size,
              ),
            ),
          ),
        );
      case StarDecor():
        final box = item.box * u;
        return frame.place(
          center: item.center,
          size: Size.square(box),
          child: Transform.rotate(
            angle: _radians(10),
            child: FadeTransition(
              opacity: motion.fadeA,
              child: ScaleTransition(
                scale: motion.scaleA,
                child: _Star(asset: layout.svgPath('ster'), box: box),
              ),
            ),
          ),
        );
      case SwayDecor():
        final size = item.size * u;
        return frame.place(
          center: item.center,
          size: Size.square(size),
          child: AnimatedBuilder(
            animation: motion.sway,
            builder: (context, child) => Transform.rotate(
              angle: _radians(motion.sway.value),
              child: child,
            ),
            child: SvgPicture.asset(
              layout.svgPath(item.asset),
              width: size,
              height: size,
            ),
          ),
        );
      case TiltedDecor():
        final size = item.size * u;
        return frame.place(
          center: item.center,
          size: Size.square(size),
          child: Transform.rotate(
            angle: _radians(item.rotation),
            child: SvgPicture.asset(
              layout.svgPath(item.asset),
              width: size,
              height: size,
            ),
          ),
        );
      case BookStackDecor():
        final unit = item.scale * u;
        return frame.place(
          center: item.center,
          size: item.size * unit,
          child: Transform.rotate(
            angle: _radians(item.rotation),
            child: _BookStack(spec: item, unit: unit, colors: colors),
          ),
        );
    }
  }
}

double _radians(double degrees) => degrees * math.pi / 180;

/// De ster-SVG zit in Figma met een vaste marge in een vierkant vak.
class _Star extends StatelessWidget {
  const _Star({required this.asset, required this.box});

  final String asset;
  final double box;

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Positioned(
          left: box * 0.1622,
          top: box * 0.1511,
          width: box * (1 - 0.1622 * 2),
          height: box * (1 - 0.1511 - 0.1946),
          child: SvgPicture.asset(asset, fit: BoxFit.fill),
        ),
      ],
    );
  }
}

class _Mascot extends StatelessWidget {
  const _Mascot({
    required this.frame,
    required this.mascot,
    required this.motion,
  });

  final _Frame frame;
  final AuthMascot mascot;
  final _AuthMotion motion;

  @override
  Widget build(BuildContext context) {
    final u = frame.uniform;
    final tilt = mascot.offsetPhase ? motion.shiftedTilt : motion.mascotTilt;
    final lift = mascot.offsetPhase ? motion.shiftedLift : motion.mascotLift;
    return frame.place(
      center: mascot.center,
      size: mascot.size * u,
      child: IgnorePointer(
        child: AnimatedBuilder(
          animation: lift,
          builder: (context, child) => Transform.translate(
            offset: Offset(0, -mascot.lift * u * lift.value),
            child: Transform.rotate(angle: _radians(tilt.value), child: child),
          ),
          child: Image.asset(
            mascot.path,
            fit: BoxFit.cover,
            excludeFromSemantics: true,
          ),
        ),
      ),
    );
  }
}

extension on BookColor {
  Color resolve(AppColors colors) => switch (this) {
    BookColor.green => const Color(0xFF43A047),
    BookColor.yellow => const Color(0xFFFFC93C),
    BookColor.darkGreen => const Color(0xFF2E7D32),
    BookColor.coral => colors.bookCoral,
    BookColor.lightGreen => colors.bookLightGreen,
    BookColor.pink => colors.bookPink,
    BookColor.orange => colors.bookOrange,
    BookColor.lime => colors.bookLime,
  };
}

/// Boekenstapel: elk boek is een gekleurde kaft met lichte bladzijden en een
/// rug aan de linkerkant.
class _BookStack extends StatelessWidget {
  const _BookStack({
    required this.spec,
    required this.unit,
    required this.colors,
  });

  final BookStackDecor spec;
  final double unit;
  final AppColors colors;

  @override
  Widget build(BuildContext context) {
    return Stack(
      clipBehavior: Clip.none,
      children: [
        // De onderste boeken eerst, zodat het bovenste boek erop ligt.
        for (var i = spec.books.length - 1; i >= 0; i--)
          ..._bookParts(spec.books[i], i),
      ],
    );
  }

  List<Widget> _bookParts(Book book, int row) {
    final h = BookStackDecor.bookHeight * unit;
    final left = book.left * unit;
    final width = book.width * unit;
    final top = row * h;
    final cover = book.color.resolve(colors);
    return [
      _block(Rect.fromLTWH(left, top, width, h), cover, h * 0.2),
      _block(
        Rect.fromLTWH(
          left + width * 0.08,
          top + h * 0.22,
          width * 0.86,
          h * 0.56,
        ),
        colors.bookPages,
        h * 0.1,
      ),
      // Rug
      _block(Rect.fromLTWH(left, top, width * 0.1, h), cover, h * 0.2),
    ];
  }

  static Widget _block(Rect rect, Color color, double radius) {
    return Positioned.fromRect(
      rect: rect,
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(radius),
        ),
      ),
    );
  }
}
